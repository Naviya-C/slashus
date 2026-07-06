package repository

import "auth-service/internal/domain/models"

type UserRepository interface{
	Create(user *models.User) error
	FindByEmail(email string)(*models.User, error)
	// Refresh Token
	SaveRefreshToken(token *models.RefreshToken) error
	DeleteRefreshToken(token string) error
	FindUserByRefreshToken(token string) (*models.User, *models.RefreshToken, error)
} 