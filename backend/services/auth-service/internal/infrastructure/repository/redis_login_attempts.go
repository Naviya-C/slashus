package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)


const lockoutWindow = 15 * time.Minute
type RedisLoginAttempts struct {
	rdb *redis.Client
}

func NewRedisLoginAttempts(rdb *redis.Client) *RedisLoginAttempts {
	return &RedisLoginAttempts{rdb: rdb}
}

func (r *RedisLoginAttempts) key(email string) string {
	return "login_attempts:" + email
}

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

func (r *RedisLoginAttempts) Reset(email string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	if err := r.rdb.Del(ctx, r.key(email)).Err(); err != nil {
		return fmt.Errorf("redis reset login attempts: %w", err)
	}
	return nil
}