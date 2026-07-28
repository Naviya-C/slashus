// Package router wires routes to backends and decides which are public.
//
// THE ROUTE TABLE IS THE SECURITY POLICY
// --------------------------------------
// Every route is either PUBLIC (no token) or PROTECTED (verified token,
// X-User-Id injected). Getting one into the wrong group is the likeliest way
// to open a hole, so the groups are registered separately and explicitly
// rather than inferred from a path prefix.
//
// Paths match the auth service as built: /api/v1/auth/... (override with
// AUTH_PREFIX).
package router

import (
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/slashus/api-gateway/internal/auth"
	"github.com/slashus/api-gateway/internal/config"
	"github.com/slashus/api-gateway/internal/middleware"
	"github.com/slashus/api-gateway/internal/proxy"
)

type Deps struct {
	Cfg      *config.Config
	Verifier *auth.Verifier
	Limiter  *middleware.RateLimiter
	Log      *slog.Logger
}

func New(d Deps) (http.Handler, error) {
	mux := http.NewServeMux()

	authProxy, err := proxy.New(d.Cfg.AuthURL, d.Cfg.ProxyTimeout, d.Log)
	if err != nil {
		return nil, err
	}
	uploadProxy, err := proxy.New(d.Cfg.UploadURL, d.Cfg.ProxyTimeout, d.Log)
	if err != nil {
		return nil, err
	}
	ingestionProxy, err := proxy.New(d.Cfg.IngestionURL, d.Cfg.ProxyTimeout, d.Log)
	if err != nil {
		return nil, err
	}
	agenticProxy, err := proxy.New(d.Cfg.AgenticURL, d.Cfg.ProxyTimeout, d.Log)
	if err != nil {
		return nil, err
	}

	prefix := d.Cfg.AuthPrefix

	// ---- gateway's own health (public) --------------------------------
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	// ---- PUBLIC ------------------------------------------------------

	mux.Handle("POST "+prefix+"/register", authProxy)
	mux.Handle("POST "+prefix+"/login", authProxy)
	mux.Handle("POST "+prefix+"/refresh", authProxy)

	mux.Handle("POST "+prefix+"/logout", authProxy)

	// ---- PROTECTED ---------------------------------------------------
	protect := func(h http.Handler) http.Handler {
		return middleware.Authenticate(d.Verifier, d.Log, h)
	}
	api := func(h http.Handler) http.Handler {
		return protect(d.Limiter.Limit("api", d.Cfg.RateLimit, d.Cfg.RateWindow, h))
	}

	// logout-all needs X-User-Id, which only this gateway can inject —
	// the auth service's routes.go expects this route to be protected.
	mux.Handle("POST "+prefix+"/logout-all", api(authProxy))
	mux.Handle("GET "+prefix+"/me", api(authProxy))

	// Uploads are limited separately and tightly: each one costs storage plus
	// a full ingestion run.
	mux.Handle("POST /uploads", protect(
		d.Limiter.Limit("upload", d.Cfg.UploadLimit, d.Cfg.UploadWindow, uploadProxy)))

	mux.Handle("GET /api/v1/user_documents", api(uploadProxy))
	

	mux.Handle("GET /jobs/{id}", api(ingestionProxy))

	for _, route := range []string{"POST /chat", "POST /mark", "GET /history"} {
		mux.Handle(route, api(agenticProxy))
	}

	// ---- global chain, outermost first --------------------------------
	//   Recovery  - catches panics from everything inside
	//   RequestID - so even a panic log carries the id
	//   Logging   - records the final status, including 401s
	//   CORS      - answers preflight before auth rejects it as tokenless
	var h http.Handler = mux
	h = middleware.CORS(d.Cfg.CORSOrigins, h)
	h = middleware.Logging(d.Log, h)
	h = middleware.RequestID(h)
	h = middleware.Recovery(d.Log, h)
	return h, nil
}
