// internal/handler/jwks_handler.go
package handler

import (
	"encoding/json"
	"net/http"

	"auth-service/internal/service"
)


type JWKSHandler struct {
	keys *service.KeyManager
}

func NewJWKSHandler(keys *service.KeyManager) *JWKSHandler {
	return &JWKSHandler{keys: keys}
}

func (h *JWKSHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	// Cache, but not for long: on rotation the gateway must pick up the new
	// key reasonably quickly, and it also re-fetches on an unknown kid.
	w.Header().Set("Cache-Control", "public, max-age=300")
	_ = json.NewEncoder(w).Encode(h.keys.JWKS())
}
