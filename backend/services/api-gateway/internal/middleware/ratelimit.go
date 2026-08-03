package middleware

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

type RateLimiter struct {
	rdb *redis.Client
	log *slog.Logger
}

func NewRateLimiter(redisURL string, log *slog.Logger) (*RateLimiter, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("parsing redis url: %w", err)
	}
	return &RateLimiter{rdb: redis.NewClient(opts), log: log}, nil
}

func (rl *RateLimiter) Close() error { return rl.rdb.Close() }

func (rl *RateLimiter) allow(ctx context.Context, key string, limit int, window time.Duration) (bool, int, error) {
	pipe := rl.rdb.TxPipeline()
	incr := pipe.Incr(ctx, key)
	pipe.Expire(ctx, key, window)
	if _, err := pipe.Exec(ctx); err != nil {
		return false, 0, err
	}
	count := int(incr.Val())
	return count <= limit, limit - count, nil
}

func (rl *RateLimiter) Limit(name string, limit int, window time.Duration, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		userID := UserIDFrom(r.Context())
		if userID == "" {
			next.ServeHTTP(w, r)
			return
		}

		key := fmt.Sprintf("ratelimit:%s:%s", name, userID)
		allowed, remaining, err := rl.allow(r.Context(), key, limit, window)
		if err != nil {
			rl.log.Error("rate limit check failed; allowing request", "err", err)
			next.ServeHTTP(w, r)
			return
		}

		w.Header().Set("X-RateLimit-Limit", strconv.Itoa(limit))
		if remaining < 0 {
			remaining = 0
		}
		w.Header().Set("X-RateLimit-Remaining", strconv.Itoa(remaining))

		if !allowed {
			w.Header().Set("Retry-After", strconv.Itoa(int(window.Seconds())))
			writeError(w, http.StatusTooManyRequests, "rate limit exceeded")
			return
		}
		next.ServeHTTP(w, r)
	})
}
