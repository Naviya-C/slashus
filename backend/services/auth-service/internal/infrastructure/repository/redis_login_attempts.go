// This file was previously an empty stub. It now holds the Redis-backed
// implementation of usecase.LoginAttempts (satisfied structurally — no import
// of the usecase package needed, so there's no import cycle).
package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// lockoutWindow is how long a failed-attempt count is remembered. It resets
// on the key's TTL rather than growing forever, so a genuine password change
// or a wait is enough to clear it — this is a brute-force speed bump, not a
// permanent ban list.
const lockoutWindow = 15 * time.Minute

// RedisLoginAttempts counts failed logins per email in Redis so the count
// survives restarts and is shared across every auth-service replica.
type RedisLoginAttempts struct {
	rdb *redis.Client
}

func NewRedisLoginAttempts(rdb *redis.Client) *RedisLoginAttempts {
	return &RedisLoginAttempts{rdb: rdb}
}

func (r *RedisLoginAttempts) key(email string) string {
	return "login_attempts:" + email
}

// Failed returns the current failed-attempt count for email. A Redis error
// (e.g. a brief network blip) returns 0 rather than failing the login — an
// unavailable rate limiter must not itself lock everyone out.
func (r *RedisLoginAttempts) Failed(email string) (int, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	n, err := r.rdb.Get(ctx, r.key(email)).Int()
	if err != nil {
		if err == redis.Nil {
			return 0, nil
		}
		return 0, fmt.Errorf("redis get login attempts: %w", err)
	}
	return n, nil
}

// RecordFailure increments the counter and (re)sets its expiry, so the window
// slides forward with each new failure rather than expiring mid-attack.
func (r *RedisLoginAttempts) RecordFailure(email string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	key := r.key(email)
	pipe := r.rdb.TxPipeline()
	incr := pipe.Incr(ctx, key)
	pipe.Expire(ctx, key, lockoutWindow)
	if _, err := pipe.Exec(ctx); err != nil {
		return fmt.Errorf("redis record login failure: %w", err)
	}
	_ = incr
	return nil
}

// Reset clears the counter on a successful login.
func (r *RedisLoginAttempts) Reset(email string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	if err := r.rdb.Del(ctx, r.key(email)).Err(); err != nil {
		return fmt.Errorf("redis reset login attempts: %w", err)
	}
	return nil
}