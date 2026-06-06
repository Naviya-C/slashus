package repository

import (
	"auth-service/internal/domain/models"

	"gorm.io/gorm"
)


type PostgresUserRepository struct {
	db *gorm.DB
}

func NewPostgresUserRepository(db *gorm.DB) *PostgresUserRepository{
	return &PostgresUserRepository{
		db: db,
	}
}

func(r *PostgresUserRepository) Create(
	user *models.User,
) error{
	return r.db.Create(user).Error
}

func(r *PostgresUserRepository) FindByEmail(
	email string,
) (*models.User, error){
	var user models.User

	err := r.db.Where("email = ?", email).First(&user).Error

	return &user, err
}