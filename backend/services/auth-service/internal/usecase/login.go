package usecase

import (
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"
	"errors"
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
) (string, error) {
	//Check User has account
	existing_user, err := l.userRepo.FindByEmail(email)

	if err != nil && existing_user == nil{
		return "", errors.New("User Not Registered")
	}
	
	hashPassword := existing_user.PasswordHash
	passwordValid := l.passwordService.Verify(password, hashPassword)

	if passwordValid != nil{
		return "", errors.New("invalid email or password")
	}

	token, err := l.jwtService.GenerateToken(existing_user.ID.String(), existing_user.Email)
	if err != nil{
		return "", errors.New("Failed to generate Authentication Token")
	}

	return token, nil

}

