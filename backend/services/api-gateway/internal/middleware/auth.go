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

const (
	HeaderUserID    = "X-User-Id"
	HeaderUserEmail = "X-User-Email"
	HeaderRequestID = "X-Request-Id"
)


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


func UserIDFrom(ctx context.Context) string {
	id, _ := ctx.Value(ctxUserID).(string)
	return id
}
