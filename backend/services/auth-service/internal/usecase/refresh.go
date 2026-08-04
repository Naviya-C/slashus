// internal/usecase/refresh.go
package usecase

import (
	"errors"
	"log/slog"
	"time"

	"auth-service/internal/domain/models"
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"
)

var ErrInvalidRefreshToken = errors.New("invalid or expired refresh token")

type RefreshUseCase struct {
	userRepo   repository.UserRepository
	jwtService service.JWTService
	log        *slog.Logger
}

func NewRefreshUseCase(
	userRepo repository.UserRepository,
	jwtService service.JWTService,
	log *slog.Logger,
) *RefreshUseCase {
	return &RefreshUseCase{userRepo: userRepo, jwtService: jwtService, log: log}
}


func (u *RefreshUseCase) RefreshToken(presented string) (accessToken, newRefresh string, err error) {
	hashed := u.jwtService.HashRefreshToken(presented)

	user, record, err := u.userRepo.FindUserByRefreshTokenHash(hashed)
	if err != nil || record == nil || user == nil {
		return "", "", ErrInvalidRefreshToken
	}

	if record.Revoked {
		u.log.Warn("refresh token reuse detected; revoking family",
			"user_id", user.ID, "family_id", record.FamilyID)
		if err := u.userRepo.RevokeFamily(record.FamilyID); err != nil {
			u.log.Error("failed to revoke token family", "err", err)
		}
		return "", "", ErrInvalidRefreshToken
	}

	if time.Now().After(record.ExpiresAt) {
		_ = u.userRepo.RevokeRefreshToken(hashed)
		return "", "", ErrInvalidRefreshToken
	}

	rawNext, hashedNext, err := u.jwtService.GenerateRefreshToken()
	if err != nil {
		return "", "", errors.New("failed to generate refresh token")
	}

	next := &models.RefreshToken{
		UserID: user.ID,
		FamilyID:  record.FamilyID,
		TokenHash: hashedNext,
		ExpiresAt: record.ExpiresAt, // do NOT extend; the session still ages out
		Revoked:   false,
		CreatedAt: time.Now(),
	}

	if err := u.userRepo.RotateRefreshToken(hashed, next); err != nil {
		return "", "", errors.New("failed to rotate refresh token")
	}

	accessToken, err = u.jwtService.GenerateTokenAccess(user.ID.String(), user.Email)
	if err != nil {
		return "", "", errors.New("failed to generate access token")
	}

	return accessToken, rawNext, nil
}
