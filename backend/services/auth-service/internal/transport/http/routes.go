package http

import (
	"net/http"

	"auth-service/internal/handler"
)


func RegisterRoutes(
	mux *http.ServeMux,
	authHandler *handler.AuthHandler,
	jwksHandler *handler.JWKSHandler,
) {
	// --- public authentication ---
	mux.HandleFunc("POST /api/v1/auth/register", authHandler.Register)
	mux.HandleFunc("POST /api/v1/auth/login", authHandler.Login)
	mux.HandleFunc("POST /api/v1/auth/refresh", authHandler.Refresh)
	mux.HandleFunc("POST /api/v1/auth/logout", authHandler.Logout)
	mux.HandleFunc("GET /api/v1/auth/me", authHandler.Me)

	// --- protected: gateway injects X-User-Id from a verified token ---
	mux.HandleFunc("POST /api/v1/auth/logout-all", authHandler.LogoutAll)

	// --- public key set ---
	mux.Handle("GET /.well-known/jwks.json", jwksHandler)

	// --- health ---
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})
}
