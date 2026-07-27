package handler

import (
	"context"
	"log/slog"
	"net/http"
	"time"

	"github.com/google/uuid"
)

// Middleware for the auth service.
//
// WHAT IS NOT HERE, AND WHY
// -------------------------
// There is no JWT-verification middleware. The gateway is the only component
// that validates tokens; this service reads the X-User-Id header the gateway
// injects. Re-verifying here would duplicate the rule in two places, and two
// copies of a security rule drift.
//
// That trust is only sound while this service is unreachable from outside. If
// auth is ever exposed directly, anyone can set X-User-Id themselves.

type ctxKey string

const (
	ctxRequestID ctxKey = "request_id"
	ctxUserID    ctxKey = "user_id"
)

const (
	HeaderRequestID = "X-Request-Id"
	HeaderUserID    = "X-User-Id"
)

// maxBodyBytes caps request bodies.
//
// Every endpoint here takes a small JSON object — an email, a password, a
// name. Without a cap, a single request with a 500 MB body is enough to
// exhaust memory, and it costs the attacker almost nothing to send.
const maxBodyBytes = 64 << 10 // 64 KiB

// Chain applies middleware so the FIRST argument is the outermost layer.
//
// Without this, wrapping by hand reverses the order you read it in, which is
// how recovery ends up inside the thing it was meant to protect.
func Chain(h http.Handler, middleware ...func(http.Handler) http.Handler) http.Handler {
	for i := len(middleware) - 1; i >= 0; i-- {
		h = middleware[i](h)
	}
	return h
}

// Recovery turns a panic into a 500 instead of killing the process.
//
// A nil dereference in one login must not drop every other in-flight request
// on the instance.
func Recovery(log *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if err := recover(); err != nil {
					log.Error("panic recovered",
						"path", r.URL.Path,
						"request_id", RequestIDFrom(r.Context()),
						"err", err,
					)
					writeJSON(w, http.StatusInternalServerError,
						map[string]string{"error": "something went wrong"})
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}

// RequestID reuses the gateway's id, or mints one when called directly.
//
// The same id appears in gateway, auth, upload and ingestion logs, so one user
// action can be followed across services instead of guessed at by timestamp.
func RequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := r.Header.Get(HeaderRequestID)
		if id == "" {
			id = uuid.NewString()
			r.Header.Set(HeaderRequestID, id)
		}
		w.Header().Set(HeaderRequestID, id)
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), ctxRequestID, id)))
	})
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

// Logging records one line per request.
//
// Never logs the body or the Authorization/Cookie headers: this service
// handles passwords and refresh tokens, and a credential written to log
// storage is a credential leaked to everyone with log access. Note the email
// is absent too — logging which addresses attempted login builds exactly the
// user list the enumeration hardening exists to prevent.
func Logging(log *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

			next.ServeHTTP(rec, r)

			log.Info("request",
				"method", r.Method,
				"path", r.URL.Path,
				"status", rec.status,
				"duration_ms", time.Since(start).Milliseconds(),
				"request_id", RequestIDFrom(r.Context()),
			)
		})
	}
}

// LimitBody caps the request body. MaxBytesReader stops reading at the limit
// rather than buffering first, so an oversized body costs the limit, not the
// whole payload.
func LimitBody(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
		next.ServeHTTP(w, r)
	})
}

// SecurityHeaders sets defensive response headers.
//
// Modest value for a JSON API, but nosniff genuinely matters: without it a
// browser may sniff a response as HTML and execute it, turning a reflected
// value into stored XSS.
func SecurityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Referrer-Policy", "no-referrer")
		// Auth responses contain tokens; caching them anywhere shared would
		// hand one user's credentials to the next.
		w.Header().Set("Cache-Control", "no-store")
		next.ServeHTTP(w, r)
	})
}

// RequireGatewayUser guards routes that act on an identified user (logout-all).
//
// It validates that X-User-Id is present and a well-formed UUID — it does NOT
// authenticate. The gateway already did that; this only catches a
// misconfiguration where the header is missing or malformed, so the handler
// can assume a usable value.
func RequireGatewayUser(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		raw := r.Header.Get(HeaderUserID)
		if raw == "" {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
			return
		}
		id, err := uuid.Parse(raw)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid user"})
			return
		}
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), ctxUserID, id)))
	})
}

// --- context accessors -----------------------------------------------------

func RequestIDFrom(ctx context.Context) string {
	id, _ := ctx.Value(ctxRequestID).(string)
	return id
}

func UserIDFrom(ctx context.Context) (uuid.UUID, bool) {
	id, ok := ctx.Value(ctxUserID).(uuid.UUID)
	return id, ok
}
