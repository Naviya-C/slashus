package main

import (
	"context" // graceful shutdown
	"errors" // compare errors
	"log/slog" // structured logging
	"net/http" // HTTP server
	"os" // environment variables
	"os/signal" // catch Ctrl+C or SIGTERM
	"syscall" // OS signals
	"time" // durations

	"auth-service/internal/config"
	"auth-service/internal/handler"
	"auth-service/internal/infrastructure/database"
	infraRedis "auth-service/internal/infrastructure/redis"
	infraRepo "auth-service/internal/infrastructure/repository"
	"auth-service/internal/service"
	transport "auth-service/internal/transport/http"
	"auth-service/internal/usecase"
)

func main() {
	log := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	if err := run(log); err != nil {
		log.Error("fatal", "err", err)
		os.Exit(1)
	}
}

func run(log *slog.Logger) error {
	cfg, err := config.LoadEnv()
	if err != nil {
		return err
	}

	db, err := database.Connect(cfg)
	if err != nil {
		return err
	}

	// --- signing keys ---------------------------------------------------
	//
	// The private key never leaves this service. Everything else in the
	// system verifies with the public half, fetched from /.well-known/jwks.json
	// — which is the whole reason for RS256 over a shared secret.
	var keys *service.KeyManager
	if cfg.DevMode {
		keys, err = service.GenerateDevKey()
		log.Warn("DEV_MODE: signing with an ephemeral in-memory key — " +
			"every restart invalidates all outstanding tokens")
	} else {
		keys, err = service.LoadKeyManager()
	}

	if err != nil {
		return err
	}

	log.Info("signing key loaded", "kid", keys.KeyID())

	// --- services -------------------------------------------------------
	passwordService := service.NewArgon2idPasswordService()

	jwtService, err := service.NewJWTService(keys, cfg.Issuer, cfg.Audience, cfg.AccessTTL)
	if err != nil {
		return err
	}

	userRepo := infraRepo.NewPostgresUserRepository(db)

	// --- use cases ------------------------------------------------------
	registerUsecase := usecase.NewRegisterUsecase(userRepo, passwordService)

	// Login lockout is backed by Redis so the failed-attempt count survives
	// restarts and is shared across every auth-service replica. If Redis is
	// unreachable at startup we still boot — an outage in the rate limiter
	// must not take down login entirely — but we log loudly, since it means
	// lockout is silently disabled until Redis comes back.
	var loginAttempts usecase.LoginAttempts
	if cfg.RedisURL == "" {
		log.Warn("REDIS_URL not set — login rate limiting is DISABLED")
	} else if rdb, rErr := infraRedis.Connect(cfg.RedisURL); rErr != nil {
		log.Error("could not connect to redis — login rate limiting is DISABLED", "err", rErr)
	} else {
		loginAttempts = infraRepo.NewRedisLoginAttempts(rdb)
		log.Info("login rate limiting enabled (redis)")
	}

	loginUseCase := usecase.NewLoginUseCase(
		userRepo, passwordService, jwtService, loginAttempts,
	)
	refreshUseCase := usecase.NewRefreshUseCase(userRepo, jwtService, log)
	logoutUseCase := usecase.NewLogoutUseCase(userRepo, jwtService)

	// --- handlers -------------------------------------------------------
	authHandler := handler.NewAuthHandler(
		registerUsecase,
		loginUseCase,
		refreshUseCase,
		logoutUseCase,
		cfg.RefreshTTL, // cookie expiry must match the DB expiry, so it is injected
	)
	jwksHandler := handler.NewJWKSHandler(keys)

	mux := http.NewServeMux()
	transport.RegisterRoutes(mux, authHandler, jwksHandler)

	// --- background: prune expired refresh tokens ------------------------
	//
	// Without this the table grows forever, and so does the unique index on
	// token_hash. Revoked-but-unexpired rows are deliberately kept: they are
	// what reuse detection matches against.
	stopCleanup := startTokenCleanup(userRepo, log)
	defer close(stopCleanup)

	port := getenv("PORT", "8081")
	srv := &http.Server{
		Addr:    ":" + port,
		Handler: mux,
		// The original called ListenAndServe with no timeouts at all. A client
		// that opens a connection and sends one byte per minute then holds a
		// goroutine indefinitely — enough of them and the service stops
		// accepting connections (slowloris).
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	// Graceful shutdown: on SIGTERM stop accepting new requests but let
	// in-flight ones finish, so a deploy does not fail a user mid-login.
	shutdownErr := make(chan error, 1)
	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
		<-quit
		log.Info("shutting down")

		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		defer cancel()
		shutdownErr <- srv.Shutdown(ctx)
	}()

	log.Info("auth service listening", "port", port, "issuer", cfg.Issuer)

	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return <-shutdownErr
}

// startTokenCleanup deletes expired refresh tokens on a schedule.
func startTokenCleanup(repo *infraRepo.PostgresUserRepository, log *slog.Logger) chan struct{} {
	stop := make(chan struct{})
	go func() {
		ticker := time.NewTicker(6 * time.Hour)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				n, err := repo.DeleteExpired()
				if err != nil {
					log.Error("token cleanup failed", "err", err)
					continue
				}
				if n > 0 {
					log.Info("pruned expired refresh tokens", "count", n)
				}
			case <-stop:
				return
			}
		}
	}()
	return stop
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
