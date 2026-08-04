// internal/usecase/logout.go
package usecase

import (
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"

	"github.com/google/uuid"
)

type LogoutUseCase struct {
	userRepo   repository.UserRepository
	jwtService service.JWTService
}

func NewLogoutUseCase(userRepo repository.UserRepository, jwtService service.JWTService) *LogoutUseCase {
	return &LogoutUseCase{userRepo: userRepo, jwtService: jwtService}
}


func (u *LogoutUseCase) Logout(presentedRefreshToken string) error {
	hashed := u.jwtService.HashRefreshToken(presentedRefreshToken)

	_, record, err := u.userRepo.FindUserByRefreshTokenHash(hashed)
	if err != nil || record == nil {
		return nil
	}
	return u.userRepo.RevokeFamily(record.FamilyID)
}


func (u *LogoutUseCase) LogoutAll(userID uuid.UUID) error {
	return u.userRepo.RevokeAllForUser(userID)
}
