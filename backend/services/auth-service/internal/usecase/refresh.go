// internal/usecase/refresh.go
package usecase

import (
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"
	"errors"
	"time"
)

type RefreshUseCase struct {
	userRepo   repository.UserRepository
	jwtService service.JWTService
}

func NewRefreshUseCase(userRepo repository.UserRepository, jwtService service.JWTService) *RefreshUseCase {
	return &RefreshUseCase{
		userRepo:   userRepo,
		jwtService: jwtService,
	} 
}

func (u *RefreshUseCase) RefreshToken(tokenStr string) (string, error) {
	// 1. Find the token and the associated user using the foreign key link
	user, tokenRecord, err := u.userRepo.FindUserByRefreshToken(tokenStr)
	if err != nil || tokenRecord == nil {
		return "", errors.New("invalid or expired refresh token")
	}

	// 2. Check if the token has expired
	if time.Now().After(tokenRecord.ExpiresAt) {
		// Clean up the expired token row from your table
		_ = u.userRepo.DeleteRefreshToken(tokenStr)
		return "", errors.New("refresh token expired")
	}

	// 3. Check the token revoked
	if tokenRecord.Revoked{
		return "", errors.New("The refresh token has been revoked")
	}

	// 3. Generate a fresh, new access token for the user
	newAccessToken, err := u.jwtService.GenerateTokenAccess(user.ID.String(), user.Email)
	if err != nil {
		return "", err
	}

	return newAccessToken, nil
}