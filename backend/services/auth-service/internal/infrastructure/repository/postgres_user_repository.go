package repository

import (
	"auth-service/internal/domain/models"

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

func(r *PostgresUserRepository) FindByEmail(
	email string,
) (*models.User, error){
	// This function checks whether the user already in the database using Email
	var user models.User

	err := r.db.Where("email = ?", email).First(&user).Error

	if err != nil{
		return nil, err
	}

	return &user, err
}