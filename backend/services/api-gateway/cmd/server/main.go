package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/slashus/api-gateway/internal/auth"
	"github.com/slashus/api-gateway/internal/config"
	"github.com/slashus/api-gateway/internal/middleware"
	"github.com/slashus/api-gateway/internal/router"
)

func main() {
	log := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	if err := run(log); err != nil {
		log.Error("fatal", "err", err)
		os.Exit(1)
	}
}

func run(log *slog.Logger) error {
	cfg, err := config.Load()
	if err != nil {
		return err
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	var verifier *auth.Verifier
	if cfg.UseJWKS() {
		verifier, err = auth.NewJWKSVerifier(ctx, cfg.JWKSURL, cfg.Issuer, cfg.Audience)
		log.Info("verifying tokens via JWKS (RS256)", "jwks", cfg.JWKSURL)
	} else {
		verifier, err = auth.NewHMACVerifier(cfg.JWTSecret, cfg.Issuer, cfg.Audience)
		log.Warn("verifying tokens with a shared HS256 secret — " +
			"the gateway can mint tokens as well as verify them; " +
			"move auth to RS256 + JWKS when you can")
	}
	if err != nil {
		return err
	}

	limiter, err := middleware.NewRateLimiter(cfg.RedisURL, log)
	if err != nil {
		return err
	}
	defer limiter.Close()

	handler, err := router.New(router.Deps{
		Cfg: cfg, Verifier: verifier, Limiter: limiter, Log: log,
	})
	if err != nil {
		return err
	}

	srv := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: handler,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       90 * time.Second,
	}

	shutdownErr := make(chan error, 1)
	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
		<-quit
		log.Info("shutting down")
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		shutdownErr <- srv.Shutdown(ctx)
	}()

	log.Info("gateway listening", "port", cfg.Port,
		"auth", cfg.AuthURL, "upload", cfg.UploadURL, "agentic", cfg.AgenticURL)

	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return <-shutdownErr
}
