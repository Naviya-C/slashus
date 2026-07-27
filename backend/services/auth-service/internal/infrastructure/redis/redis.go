// Package redis provides the auth service's Redis connection and the
// Redis-backed login attempt limiter used to slow brute-force login attempts.
//
// This was previously an empty stub: main.go passed a nil LoginAttempts,
// which disables lockout entirely (unlimited password guesses per account).
package redis

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// Connect parses redisURL and pings the server once so a bad URL or an
// unreachable Redis fails fast at startup instead of on the first login.
func Connect(redisURL string) (*redis.Client, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("parsing redis url: %w", err)
	}
	client := redis.NewClient(opts)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("connecting to redis: %w", err)
	}
	return client, nil
}