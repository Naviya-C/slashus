// internal/handler/jwks_handler.go
package handler

import (
	"encoding/json"
	"net/http"

	"auth-service/internal/service"
)

// JWKSHandler publishes the PUBLIC signing keys.
//
// This endpoint is what lets the gateway verify RS256 tokens without ever
// holding a signing key, and without calling this service on every request:
// it fetches once, caches, and re-fetches only when it sees an unknown kid.
//
// Publicly readable by design — public keys are meant to be public. Serving
// them is not a disclosure; it is the point.
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
