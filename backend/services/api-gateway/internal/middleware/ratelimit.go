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

// RateLimiter caps requests per USER, not per IP.
//
// Per-IP would be wrong here: a whole school behind one NAT shares an address,
// so one student's activity would throttle everyone else. The user id from the
// verified token is the correct unit.
//
// Counters live in Redis rather than in memory so the limit holds across
// gateway replicas. An in-process counter silently doubles the effective limit
// the moment you run two instances.
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

// allow implements a fixed-window counter: INCR a key that expires after the
// window.
//
// Fixed window has a known flaw — a client can send `limit` requests at the end
// of one window and `limit` again at the start of the next, briefly doubling
// the rate. That is acceptable here (the limits are about cost control, not
// precise fairness). Swap for a sliding window if it ever matters.
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

// Limit returns middleware enforcing `limit` requests per `window` per user.
//
// `name` scopes the counter so different route groups get independent budgets:
// uploads are expensive and capped tightly, chat more generously.
func (rl *RateLimiter) Limit(name string, limit int, window time.Duration, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		userID := UserIDFrom(r.Context())
		if userID == "" {
			// Unauthenticated routes are not rate limited here; they are
			// public by design and protected at the auth service.
			next.ServeHTTP(w, r)
			return
		}

		key := fmt.Sprintf("ratelimit:%s:%s", name, userID)
		allowed, remaining, err := rl.allow(r.Context(), key, limit, window)
		if err != nil {
			// FAIL OPEN. If Redis is down, a closed failure would take the
			// whole product offline to enforce a cost control. Log loudly and
			// let the request through.
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
