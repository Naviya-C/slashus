package http

import (
	"net/http"

	"auth-service/internal/handler"
)

func RegisterRoutes(
	mux *http.ServeMux,
	authHandler *handler.AuthHandler,
) {
	mux.HandleFunc(
		"POST /register",
		authHandler.Register,
	)
}