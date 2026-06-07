package main

import (
	"log"
	"net/http"

	"auth-service/internal/config"
	"auth-service/internal/handler"
	"auth-service/internal/infrastructure/database"
	infraRepo "auth-service/internal/infrastructure/repository"
	transport "auth-service/internal/transport/http"
	"auth-service/internal/service"
	"auth-service/internal/usecase"
)

func main() {

	cfg, err := config.LoadEnv()

	if err != nil {
		log.Fatal(err)
	}

	db, err := database.Connect(cfg)

	if err != nil {
		log.Fatal(err)
	}

	userRepo := infraRepo.NewPostgresUserRepository(db)

	passwordService :=
		service.NewArgon2idPasswordService()

	registerUsecase :=
		usecase.NewRegisterUsecase(
			userRepo,
			passwordService,
		)

	authHandler :=
		handler.NewAuthHandler(
			registerUsecase,
		)

	mux := http.NewServeMux()

	transport.RegisterRoutes(
		mux,
		authHandler,
	)

	log.Println("Server running on :8080")

	log.Fatal(
		http.ListenAndServe(":8080", mux),
	)
}