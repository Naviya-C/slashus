package handler

import (
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"time"

	dto "auth-service/internal/transport"
	"auth-service/internal/usecase"

	"github.com/google/uuid"
)

const refreshCookieName = "refresh_token"
const refreshCookiePath = "/api/v1/auth"

func sameSiteFromEnv() http.SameSite {
	switch os.Getenv("COOKIE_SAMESITE") {
	case "none":
		return http.SameSiteNoneMode
	case "lax":
		return http.SameSiteLaxMode
	default:
		return http.SameSiteStrictMode
	}
}

type AuthHandler struct {
	registerUseCase 		*usecase.RegisterUsecase
	loginUseCase    		*usecase.LoginUseCase
	refreshUseCase  		*usecase.RefreshUseCase
	logoutUseCase   		*usecase.LogoutUseCase
	refreshTTL      		time.Duration
	secureCookies   		bool
	googleLoginUseCase		*usecase.GoogleLoginUseCase
	// Remove in production
	sameSite        		http.SameSite
	
	userProfileUseCase		*usecase.ProfileUseCase
	
}

func NewAuthHandler(
	registerUsecase *usecase.RegisterUsecase,
	loginUseCase *usecase.LoginUseCase,
	refreshUseCase *usecase.RefreshUseCase,
	logoutUseCase *usecase.LogoutUseCase,
	refreshTTL time.Duration,
	userProfileUseCase	*usecase.ProfileUseCase,
	googleLoginUseCase	*usecase.GoogleLoginUseCase,
) *AuthHandler {
	return &AuthHandler{
		registerUseCase: registerUsecase,
		loginUseCase:    loginUseCase,
		refreshUseCase:  refreshUseCase,
		logoutUseCase:   logoutUseCase,
		refreshTTL:      refreshTTL,
		secureCookies: os.Getenv("SECURE_COOKIES") != "false",
		// This uses for profile detail fetch when login to dashboard '/me' endpoint
		userProfileUseCase:	userProfileUseCase,
		// delete production
		sameSite:      sameSiteFromEnv(),
		googleLoginUseCase: googleLoginUseCase,
	}
}

// --- helpers ---------------------------------------------------------------

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}


func writeAuthError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, usecase.ErrInvalidCredentials):
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "invalid email or password"})
	case errors.Is(err, usecase.ErrAccountLocked):
		writeJSON(w, http.StatusTooManyRequests, map[string]string{"error": "too many failed attempts; try again later"})
	case errors.Is(err, usecase.ErrInvalidRefreshToken):
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "session expired; please log in again"})
	default:
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "something went wrong"})
	}
}

func (h *AuthHandler) setRefreshCookie(w http.ResponseWriter, token string) {
	http.SetCookie(w, &http.Cookie{
		Name:     refreshCookieName,
		Value:    token,
		Expires:  time.Now().Add(h.refreshTTL),
		MaxAge:   int(h.refreshTTL.Seconds()),
		HttpOnly: true, // unreadable from JavaScript, so XSS cannot exfiltrate it
		Secure:   h.secureCookies,
		SameSite: h.sameSite,//http.SameSiteStrictMode, // not sent on cross-site requests: CSRF mitigation
		Path:     refreshCookiePath,
	})
}


func (h *AuthHandler) clearRefreshCookie(w http.ResponseWriter) {
	http.SetCookie(w, &http.Cookie{
		Name:     refreshCookieName,
		Value:    "",
		Expires:  time.Unix(0, 0),
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   h.secureCookies,
		SameSite: h.sameSite,//http.SameSiteStrictMode,
		Path:     refreshCookiePath,
	})
}

// --- handlers --------------------------------------------------------------

func (h *AuthHandler) Register(w http.ResponseWriter, r *http.Request) {
	var req dto.RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
		return
	}

	if err := h.registerUseCase.Register(req.FirstName, req.LastName, req.Email, req.Password); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{
			"error": "could not complete registration",
		})
		return
	}

	writeJSON(w, http.StatusCreated, map[string]string{"message": "user registered successfully"})
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var req dto.LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
		return
	}

	accessToken, refreshToken, err := h.loginUseCase.Login(req.Email, req.Password)
	if err != nil {
		writeAuthError(w, err)
		return
	}

	h.setRefreshCookie(w, refreshToken)

	writeJSON(w, http.StatusOK, map[string]any{
		"message":    "login success",
		"token":      accessToken,
		"expires_in": 900, // seconds; lets the client refresh before expiry
	})
}


func (h *AuthHandler) Refresh(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(refreshCookieName)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "missing refresh token"})
		return
	}

	accessToken, newRefreshToken, err := h.refreshUseCase.RefreshToken(cookie.Value)
	if err != nil {
		h.clearRefreshCookie(w)
		writeAuthError(w, err)
		return
	}

	h.setRefreshCookie(w, newRefreshToken)

	writeJSON(w, http.StatusOK, map[string]any{
		"token":      accessToken,
		"expires_in": 900,
	})
}


func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	if cookie, err := r.Cookie(refreshCookieName); err == nil {
		_ = h.logoutUseCase.Logout(cookie.Value)
	}
	h.clearRefreshCookie(w)
	writeJSON(w, http.StatusOK, map[string]string{"message": "logged out"})
}


func (h *AuthHandler) LogoutAll(w http.ResponseWriter, r *http.Request) {
	userID, err := uuid.Parse(r.Header.Get("X-User-Id"))
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid user"})
		return
	}

	if err := h.logoutUseCase.LogoutAll(userID); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "something went wrong"})
		return
	}

	h.clearRefreshCookie(w)
	writeJSON(w, http.StatusOK, map[string]string{"message": "logged out of all devices"})
}

// This handler for user login and landing page handling mean /me router.

func (h *AuthHandler) Me(w http.ResponseWriter, r *http.Request) {
	userID, err := uuid.Parse(r.Header.Get("X-User-Id"))
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid user"})
		return
	}

	user, err := h.userProfileUseCase.GetByID(userID)
	if err != nil {
		if errors.Is(err, usecase.ErrUserNotFound) {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "user not found"})
			return
		}
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "something went wrong"})
		return
	}


	writeJSON(w, http.StatusOK, dto.UserMe{
		UserId:     user.ID,
		FirstName: 	user.FirstName,
		LastName:  	user.LastName,
		Email:     	user.Email,
		CreatedAt: 	user.CreatedAt,
	})
}
