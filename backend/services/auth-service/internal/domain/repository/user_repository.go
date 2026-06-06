package repository

import "auth-service/internal/domain/models"

type UserRepository interface{
	Create(user *models.User) error
	FindByEmail(email string)(*models.User, error)
}