package usecase

import (
	"auth-service/internal/domain/models"
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"
	"errors"
	"time"
)

type LoginUseCase struct{
	userRepo repository.UserRepository
	passwordService service.PasswordService
	jwtService service.JWTService
}

func ExistingLoginUseCase(
	useRepo repository.UserRepository,
	passwordService service.PasswordService,
	jwtService service.JWTService,
) *LoginUseCase{
	return &LoginUseCase{
		userRepo: useRepo,
		passwordService: passwordService,
		jwtService: jwtService,
	}
}


func (l *LoginUseCase) Login(
	email string,
	password string,
) (string, string, error) {
	//Check User has account
	existing_user, err := l.userRepo.FindByEmail(email)

	if err != nil && existing_user == nil{
		return "", "", errors.New("User Not Registered")
	}
	
	hashPassword := existing_user.PasswordHash
	passwordValid := l.passwordService.Verify(password, hashPassword)

	if passwordValid != nil{
		return "", "", errors.New("invalid email or password")
	}

	accessToken, err := l.jwtService.GenerateTokenAccess(existing_user.ID.String(), existing_user.Email)
	if err != nil{
		return "", "", errors.New("Failed to generate Authentication Token")
	}

	refreshToken, err := l.jwtService.GenerateRefreshToken()
	if err != nil{
		return "", "", errors.New("Failed to Generate Refresh Token")
	}

	refreshTokenRecord := &models.RefreshToken{
		UserID: existing_user.ID,
		TokenHash: refreshToken,
		ExpiresAt: time.Now().Add(time.Hour * 24 * 45), // 45 Days after refresh token get expires
		Revoked: false,
		CreatedAt: time.Now(),
	}

	err = l.userRepo.SaveRefreshToken(refreshTokenRecord)
    if err != nil {
        return "", "", errors.New("failed to secure login session")
    }

	return accessToken, refreshToken, nil
}

