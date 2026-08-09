// internal/handler/oauth_handler.go
package handler

import (
	"encoding/json"
	"errors"
	"net/http"

	"auth-service/internal/service"
	"auth-service/internal/usecase"
)


func (h *AuthHandler) GoogleLogin(w http.ResponseWriter, r *http.Request) {
	var req struct {
		IDToken string `json:"id_token"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
		return
	}
	if req.IDToken == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "id_token is required"})
		return
	}
	if h.googleLoginUseCase == nil {
		writeJSON(w, http.StatusNotImplemented, map[string]string{
			"error": "google sign-in is not enabled",
		})
		return
	}

	accessToken, refreshToken, err := h.googleLoginUseCase.Login(r.Context(), req.IDToken)
	if err != nil {
		writeGoogleError(w, err)
		return
	}

	h.setRefreshCookie(w, refreshToken)

	writeJSON(w, http.StatusOK, map[string]any{
		"message":    "login success",
		"token":      accessToken,
		"expires_in": 900,
	})
}

func writeGoogleError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, usecase.ErrEmailHasPassword):
		writeJSON(w, http.StatusConflict, map[string]string{
			"error": "This email is already registered. Sign in with your password, " +
				"then link Google from your account settings.",
			"code": "email_has_password",
		})

	case errors.Is(err, service.ErrEmailNotVerified):
		writeJSON(w, http.StatusForbidden, map[string]string{
			"error": "Your Google account email is not verified.",
			"code":  "email_not_verified",
		})

	case errors.Is(err, service.ErrInvalidGoogleToken):
		writeJSON(w, http.StatusUnauthorized, map[string]string{
			"error": "google sign-in failed",
			"code":  "invalid_token",
		})

	default:
		writeJSON(w, http.StatusInternalServerError, map[string]string{
			"error": "google sign-in failed",
		})
	}
}