package usecase

import (
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"
	"errors"
)

type LoginUseCase struct{
	userRepo repository.UserRepository
	passwordService service.PasswordService
}

func ExistingLoginUseCase(
	useRepo repository.UserRepository,
	passwordService service.PasswordService,
) *LoginUseCase{
	return &LoginUseCase{
		userRepo: useRepo,
		passwordService: passwordService,
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

	token := "dfd"

	return token, nil

}

