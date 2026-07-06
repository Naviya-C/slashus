package handler

import (
	dto "auth-service/internal/transport"
	"auth-service/internal/usecase"
	"encoding/json"
	"net/http"
	"time"
)


type AuthHandler struct{
	registerUseCase *usecase.RegisterUsecase
	loginUseCase *usecase.LoginUseCase
	refreshUseCase *usecase.RefreshUseCase
}

func NewAuthHandler(
	registerUsecase *usecase.RegisterUsecase,
	loginUseCase *usecase.LoginUseCase,
	refreshToken *usecase.RefreshUseCase,
) *AuthHandler{
	return &AuthHandler{
		registerUseCase: registerUsecase,
		loginUseCase: loginUseCase,
		refreshUseCase: refreshToken,
	}
}

func(h *AuthHandler) Register(
	w http.ResponseWriter,
	r *http.Request,
){

	var req dto.RegisterRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil{
		http.Error(w, "Invalid Request", http.StatusBadRequest)
		return
	}

	err := h.registerUseCase.Register(
		req.FirstName,
		req.LastName,
		req.Email,
		req.Password,
	)

	if err != nil{
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.WriteHeader(http.StatusCreated)

	json.NewEncoder(w).Encode(map[string]string{
		"message": "user registered successfully",
	})

}

func (l *AuthHandler) Login(
	w http.ResponseWriter,
	r *http.Request,
){
	var req dto.LoginRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil{
		http.Error(w, "Invalid Request", http.StatusBadRequest)
		return
	}

	token, refToken, err := l.loginUseCase.Login(req.Email, req.Password)

	if err != nil{
		http.Error(w, err.Error(), http.StatusUnauthorized)
		return
	}

	http.SetCookie(w, &http.Cookie{
        Name:     "refresh_token",
        Value:    refToken,
        Expires:  time.Now().Add(time.Hour * 24 * 45), // Matches your 45-day DB expiry
        HttpOnly: true,                                // 🔒 Protects against XSS attacks
        Secure:   false,                               // Set to 'true' in production (requires HTTPS)
        SameSite: http.SameSiteStrictMode,             // Mitigates CSRF attacks
        Path:     "/",                                 // Accessible throughout the app
    })

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	json.NewEncoder(w).Encode(map[string]string{
		"message": "Login Success",
		"token": token,
	})
}

func (h *AuthHandler) Refresh(
    w http.ResponseWriter,
    r *http.Request,
) {
    // 1. Get the refresh token out of the secure cookie
    cookie, err := r.Cookie("refresh_token")
    if err != nil {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusUnauthorized)
        json.NewEncoder(w).Encode(map[string]string{"error": "Missing refresh token"})
        return
    }

    // 2. Validate token, state, and expiration via UseCase
    newAccessToken, err := h.refreshUseCase.RefreshToken(cookie.Value)
    if err != nil {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusUnauthorized)
        json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
        return
    }

    // 3. Hand back the new short-lived access token
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(map[string]string{
        "token": newAccessToken,
    })
}