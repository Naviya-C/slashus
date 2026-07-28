// internal/usecase/profile.go
package usecase
 
import (
	"errors"
 
	"auth-service/internal/domain/models"
	"auth-service/internal/domain/repository"
 
	"github.com/google/uuid"
)

var ErrUserNotFound = errors.New("User not found")

type ProfileUseCase struct{
	userRepo repository.UserRepository
}

func NewProfileUseCase(
	userRepo repository.UserRepository,
) *ProfileUseCase{
	return &ProfileUseCase{
		userRepo: userRepo,
	}
}

func (u *ProfileUseCase) GetByID(id uuid.UUID) (*models.User, error){
	user, err := u.userRepo.FindByID(id)
	if err != nil{
		return nil, err
	}

	if user == nil{
		return nil, ErrUserNotFound
	}

	return user, nil
}