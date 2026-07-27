// Package config loads gateway settings from the environment.
//
// Backends are URLs rather than compile-time constants, so services can be
// deployed one at a time: a backend that is not up yet returns 502 on its own
// routes while everything else keeps working.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/joho/godotenv"
)

type Config struct {
	Port string

	// --- token verification: set exactly one ---
	//
	// JWTSecret  -> HS256, shared secret. Matches the auth service as built.
	// JWKSURL    -> RS256, public keys fetched from auth. Preferred long term:
	//               the gateway can then verify but never MINT tokens.
	JWTSecret string
	JWKSURL   string

	// Optional claim checks. Enforced only when set — the auth service does
	// not emit iss/aud yet. Set these once it does; a token minted by the same
	// issuer for a different application would otherwise be accepted here.
	Issuer   string
	Audience string

	// Backend service URLs (internal docker network names in production).
	AuthURL      string
	UploadURL    string
	IngestionURL string
	AgenticURL   string

	// Path prefix the auth service actually serves on.
	AuthPrefix string

	// Rate limiting.
	RedisURL     string
	RateLimit    int
	RateWindow   time.Duration
	UploadLimit  int
	UploadWindow time.Duration

	CORSOrigins []string

	ProxyTimeout time.Duration
}

func Load() (*Config, error) {
	_ = godotenv.Load()

	cfg := &Config{
		Port:      getenv("PORT", "8080"),
		JWTSecret: os.Getenv("JWT_SECRET"),
		JWKSURL:   os.Getenv("JWKS_URL"),
		Issuer:    os.Getenv("JWT_ISSUER"),
		Audience:  os.Getenv("JWT_AUDIENCE"),

		AuthURL:      getenv("AUTH_URL", "http://auth:8081"),
		UploadURL:    getenv("UPLOAD_URL", "http://upload:8082"),
		IngestionURL: getenv("INGESTION_URL", "http://ingestion:8083"),
		AgenticURL:   getenv("AGENTIC_URL", "http://agentic:8084"),

		AuthPrefix: getenv("AUTH_PREFIX", "/api/v1/auth"),

		RedisURL:     os.Getenv("REDIS_URL"),
		RateLimit:    getenvInt("RATE_LIMIT", 60),
		RateWindow:   getenvDuration("RATE_WINDOW", time.Minute),
		UploadLimit:  getenvInt("UPLOAD_RATE_LIMIT", 10),
		UploadWindow: getenvDuration("UPLOAD_RATE_WINDOW", time.Hour),

		CORSOrigins: strings.Split(getenv("CORS_ORIGINS", "http://localhost:8501"), ","),

		ProxyTimeout: getenvDuration("PROXY_TIMEOUT", 5*time.Minute),
	}

	// Fail closed on ambiguous or absent verification config. A gateway that
	// starts without knowing how to verify tokens is worse than one that
	// refuses to start: it would have to either reject everything or, worse,
	// let requests through unchecked.
	switch {
	case cfg.JWTSecret == "" && cfg.JWKSURL == "":
		return nil, fmt.Errorf("set JWT_SECRET (HS256) or JWKS_URL (RS256)")
	case cfg.JWTSecret != "" && cfg.JWKSURL != "":
		return nil, fmt.Errorf("set only one of JWT_SECRET or JWKS_URL, not both")
	}

	if cfg.RedisURL == "" {
		return nil, fmt.Errorf("REDIS_URL is required for rate limiting")
	}
	return cfg, nil
}

// UseJWKS reports whether the gateway should verify RS256 tokens via JWKS.
func (c *Config) UseJWKS() bool { return c.JWKSURL != "" }

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getenvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return fallback
}

func getenvDuration(key string, fallback time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return fallback
}
