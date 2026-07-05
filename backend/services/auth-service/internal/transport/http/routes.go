package http

import (
	"net/http"
	"auth-service/internal/handler"
)

// RegisterRoutes hooks up the HTTP endpoints to their respective handler methods.
func RegisterRoutes(mux *http.ServeMux, authHandler *handler.AuthHandler) {
	
	// Public Authentication Routes
	mux.HandleFunc("POST /api/v1/auth/register", authHandler.Register)
	mux.HandleFunc("POST /api/v1/auth/login", authHandler.Login)
	
	// Example of adding a health check endpoint directly
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"OK"}`))
	})
}