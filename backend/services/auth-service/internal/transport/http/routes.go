package http

import (
	"net/http"

	"auth-service/internal/handler"
)

// RegisterRoutes hooks up the HTTP endpoints to their handler methods.
//
// WHICH ROUTES ARE PUBLIC
// -----------------------
// This service does not verify tokens — the gateway does. So "public" and
// "protected" here describe what the GATEWAY must enforce, and the two lists
// have to agree. A route the gateway protects but this service does not expect
// to be protected is merely broken; the reverse is a security hole.
//
//	public    register, login, refresh, logout, jwks, health
//	protected logout-all  (needs X-User-Id, which only the gateway can set)
//
// Note logout is PUBLIC: it authenticates with the refresh cookie, not a
// bearer token. Requiring a valid access token to log out would leave a user
// with an expired token unable to end their session — exactly when they most
// want to.
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
	//
	// Served at the well-known path at the ROOT, not under /api/v1/auth: it is
	// not an auth operation, it is discovery metadata, and RFC 8414 puts it
	// here. The gateway's JWKS_URL must match this exactly.
	//
	// Public by design. Publishing public keys is the point — it is what lets
	// the gateway verify RS256 tokens without ever holding a signing key.
	mux.Handle("GET /.well-known/jwks.json", jwksHandler)

	// --- health ---
	//
	// Liveness only: it deliberately does not probe Postgres or Redis. A
	// readiness check that calls dependencies turns their brief outage into a
	// container restart loop, which makes a short problem into a long one.
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})
}
