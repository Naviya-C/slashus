// Package middleware holds the gateway's request pipeline.
package middleware

import (
	"context"
	"log/slog"
	"net/http"
	"strings"

	"github.com/slashus/api-gateway/internal/auth"
)

type ctxKey string

const (
	ctxUserID    ctxKey = "user_id"
	ctxRequestID ctxKey = "request_id"
)

// Headers the gateway injects for backends. Backends read these and trust them
// completely, which is safe only because backends are not publicly reachable.
const (
	HeaderUserID    = "X-User-Id"
	HeaderUserEmail = "X-User-Email"
	HeaderRequestID = "X-Request-Id"
)

// Authenticate verifies the bearer token and rewrites the request for
// downstream services.
//
// THE TRUST BOUNDARY
// ------------------
// Two rewrites happen here, and both matter:
//
//  1. INJECT X-User-Id from the verified `sub` claim. This is the identity
//     every backend uses to scope its data.
//
//  2. STRIP the Authorization header. Backends never see the raw token, so a
//     compromised backend cannot replay a user's credentials against other
//     services. It also stops a backend from "helpfully" re-verifying and
//     drifting from the gateway's rules.
//
// We also delete any INBOUND X-User-Id before setting our own. A client that
// sends its own X-User-Id must not be able to smuggle it through — without
// this line, the entire identity model is bypassable with one curl flag.
func Authenticate(v *auth.Verifier, log *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Defensive: clear anything the client tried to inject.
		r.Header.Del(HeaderUserID)
		r.Header.Del(HeaderUserEmail)

		header := r.Header.Get("Authorization")
		if !strings.HasPrefix(header, "Bearer ") {
			writeError(w, http.StatusUnauthorized, "missing bearer token")
			return
		}
		token := strings.TrimSpace(strings.TrimPrefix(header, "Bearer "))

		claims, err := v.Verify(token)
		if err != nil {
			// Deliberately vague to the client; the detail goes to logs only.
			log.Debug("token rejected", "err", err)
			writeError(w, http.StatusUnauthorized, "invalid or expired token")
			return
		}

		r.Header.Set(HeaderUserID, claims.UserID)
		if claims.Email != "" {
			r.Header.Set(HeaderUserEmail, claims.Email)
		}
		r.Header.Del("Authorization")

		ctx := context.WithValue(r.Context(), ctxUserID, claims.UserID)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// UserIDFrom returns the authenticated user id, if any. Used by rate limiting,
// which must key on the user rather than the IP.
func UserIDFrom(ctx context.Context) string {
	id, _ := ctx.Value(ctxUserID).(string)
	return id
}
