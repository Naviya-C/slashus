package repository

import (
	"auth-service/internal/domain/models"
	"errors"
	"gorm.io/gorm"
)


type PostgresUserRepository struct {
	db *gorm.DB
}

func NewPostgresUserRepository(db *gorm.DB) *PostgresUserRepository{
	//Use to connect database connection.
	return &PostgresUserRepository{
		db: db,
	}
}

func(r *PostgresUserRepository) Create(
	user *models.User,
) error{
	// This function create a new user in database
	return r.db.Create(user).Error
}

func (r *PostgresUserRepository) FindByEmail(email string) (*models.User, error) {
    var user models.User

    err := r.db.Where("email = ?", email).First(&user).Error
    if err != nil {
        // If the record simply doesn't exist, return nil for both, meaning "no user found"
        if errors.Is(err, gorm.ErrRecordNotFound) {
            return nil, nil
        }
        // Return actual database connection or system errors
        return nil, err
    }

    return &user, nil
}

func (r *PostgresUserRepository) SaveRefreshToken(
	token *models.RefreshToken) error {
	return r.db.Create(token).Error
}

func (r *PostgresUserRepository) DeleteRefreshToken(
	tokenStr string) error {
	return r.db.Where("token_hash = ?", tokenStr).Delete(&models.RefreshToken{}).Error
}

func (r *PostgresUserRepository) FindUserByRefreshToken(tokenStr string) (*models.User, *models.RefreshToken, error) {
	var tokenRecord models.RefreshToken
	
	// Find the token row first
	if err := r.db.Where("token_hash = ?", tokenStr).First(&tokenRecord).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil, nil // Token not found cleanly
		}
		return nil, nil, err
	}

	// Use the UserID foreign key to get the corresponding User details
	var user models.User
	if err := r.db.First(&user, "id = ?", tokenRecord.UserID).Error; err != nil {
		return nil, nil, err
	}

	return &user, &tokenRecord, nil
}