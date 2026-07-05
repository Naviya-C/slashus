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