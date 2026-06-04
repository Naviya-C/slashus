package models

import (
	"time"
	"github.com/google/uuid"
)


type User struct {
	ID				uuid.UUID		`gorm:"type:uuid;default:gen_random_uuid();primaryKey"`
	FirstName		string			`gorm:"size:50;not null"`
	LastName		string			`gorm:"size:50;not null"`
	Email			string			`gorm:"size:100;not null;unique"`
	PasswordHash	string			`gorm:"not null"`
	CreatedAt		time.Time	
	UpdatedAt		time.Time

	RefreshTokens []RefreshToken 	`gorm:"foreignKey:UserID"`
} 