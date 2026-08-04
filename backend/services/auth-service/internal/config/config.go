package config

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/joho/godotenv"
)

type Config struct {
	DatabaseURL   string
	DatabaseURL_P string

	// --- token signing ---
	PrivateKeyPEM  string
	PrivateKeyFile string
	Issuer   string
	Audience string
 
	AccessTTL  time.Duration
	RefreshTTL time.Duration

	RedisURL string
	DevMode bool
}

func LoadEnv() (*Config, error) {
	_ = godotenv.Load()

	cfg := &Config{
		DatabaseURL:    os.Getenv("DATABASE_URL"),
		DatabaseURL_P:  os.Getenv("DATABASE_URL_P"),
		PrivateKeyPEM:  os.Getenv("JWT_PRIVATE_KEY"),
		PrivateKeyFile: os.Getenv("JWT_PRIVATE_KEY_FILE"),
		Issuer:         os.Getenv("JWT_ISSUER"),
		Audience:       os.Getenv("JWT_AUDIENCE"),
		RedisURL:       os.Getenv("REDIS_URL"),
		AccessTTL:      getDuration("ACCESS_TOKEN_TTL", 15*time.Minute),
		RefreshTTL:     getDuration("REFRESH_TOKEN_TTL", 30*24*time.Hour),
		DevMode:        os.Getenv("DEV_MODE") == "true",
	}

	var missing []string
	if cfg.DatabaseURL == "" {
		missing = append(missing, "DATABASE_URL")
	}
	if cfg.DatabaseURL_P == "" {
		missing = append(missing, "DATABASE_URL_P")
	}
	if cfg.Issuer == "" {
		missing = append(missing, "JWT_ISSUER")
	}
	if cfg.Audience == "" {
		missing = append(missing, "JWT_AUDIENCE")
	}
	if !cfg.DevMode && cfg.PrivateKeyPEM == "" && cfg.PrivateKeyFile == "" {
		missing = append(missing, "JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_FILE")
	}
	if len(missing) > 0 {
		return nil, fmt.Errorf("missing required config: %s", strings.Join(missing, ", "))
	}

	if cfg.AccessTTL > time.Hour {
		return nil, fmt.Errorf("ACCESS_TOKEN_TTL of %s is too long; keep it under 1h", cfg.AccessTTL)
	}
	return cfg, nil
}

func getDuration(key string, fallback time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return fallback
}
