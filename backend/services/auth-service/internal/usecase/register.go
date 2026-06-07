package usecase

import (
	"errors"

	"auth-service/internal/domain/models"
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"
)

type RegisterUsecase struct {
	userRepo        repository.UserRepository
	passwordService service.PasswordService
}

func NewRegisterUsecase(
	userRepo repository.UserRepository,
	passwordService service.PasswordService,
) *RegisterUsecase {
	return &RegisterUsecase{
		userRepo:        userRepo,
		passwordService: passwordService,
	}
}

func (u *RegisterUsecase) Register(
	firstName string,
	lastName string,
	email string,
	password string,
) error {

	// Check if email already exists
	existingUser, err := u.userRepo.FindByEmail(email)

	if err == nil && existingUser != nil {
		return errors.New("email already exists")
	}

	// Hash password
	hash, err := u.passwordService.Hash(password)

	if err != nil {
		return err
	}

	// Create user object
	user := &models.User{
		FirstName:   firstName,
		LastName:    lastName,
		Email:       email,
		PasswordHash: hash,
	}

	// Save user
	err = u.userRepo.Create(user)

	if err != nil {
		return err
	}

	return nil
}