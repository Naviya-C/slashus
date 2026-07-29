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

// refreshCookieName is scoped to the auth path on purpose — see setRefreshCookie.
const refreshCookieName = "refresh_token"
const refreshCookiePath = "/api/v1/auth"

// Local dev only: the frontend runs on localhost while the API is on
// api.slashus.com — different sites, so a Strict cookie is never sent and
// refresh 401s forever. Production leaves this unset and keeps Strict.
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
		secureCookies: os.Getenv("SECURE_COOKIES") != "false",
		sameSite:      sameSiteFromEnv(),
	}
}

// --- helpers ---------------------------------------------------------------

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

// writeAuthError maps known errors to safe messages.
//
// The original passed err.Error() straight to the client. That leaks internals
// ("failed to secure login session" tells an attacker the database is
// reachable but the write failed) and, worse, would have leaked any
// enumeration-revealing message the use case produced. Only the two errors
// that are safe to disclose are echoed; everything else becomes a generic 500.
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

// clearRefreshCookie must mirror Name, Path, Secure and SameSite exactly, or
// the browser treats it as a DIFFERENT cookie and the original survives —
// leaving the user "logged out" in the UI while still holding a live token.
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
		// Deliberately generic. "email already registered" is an enumeration
		// oracle: it confirms an address exists on your platform, which is
		// exactly what login was hardened against leaking.
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

	// The access token goes in the BODY, not a cookie: the client holds it in
	// memory and sends it as a bearer header. A cookie would be attached
	// automatically to every request, which is what makes CSRF possible.
	writeJSON(w, http.StatusOK, map[string]any{
		"message":    "login success",
		"token":      accessToken,
		"expires_in": 900, // seconds; lets the client refresh before expiry
	})
}

// Refresh exchanges the refresh token for a NEW access token AND a NEW refresh
// token.
//
// The rotation is the point: the presented token is consumed, so a copy of it
// held by anyone else becomes useless — and its later use is detected. The new
// cookie MUST be set here, or the client is left holding a token that was just
// revoked and every subsequent refresh fails.
func (h *AuthHandler) Refresh(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(refreshCookieName)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "missing refresh token"})
		return
	}

	accessToken, newRefreshToken, err := h.refreshUseCase.RefreshToken(cookie.Value)
	if err != nil {
		// Clear the cookie: whatever the client holds is now invalid, either
		// because it expired or because reuse was detected and the family was
		// revoked. Leaving it would send the browser into a refresh loop.
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

// Logout revokes the session's whole token family and clears the cookie.
//
// Always returns 200, even for an unknown or missing token. Logout must be
// idempotent — a client retrying after a network blip should not see an error
// — and reporting "no such token" would let an attacker probe which tokens are
// still live.
func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	if cookie, err := r.Cookie(refreshCookieName); err == nil {
		_ = h.logoutUseCase.Logout(cookie.Value)
	}
	h.clearRefreshCookie(w)
	writeJSON(w, http.StatusOK, map[string]string{"message": "logged out"})
}

// LogoutAll ends every session for the user — "sign out of all devices", and
// the correct response to a password change or a suspected compromise.
//
// The user id comes from X-User-Id, injected by the gateway from a verified
// token. This service never re-verifies; the gateway is the only validator,
// and it is the only party that can set this header.
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
