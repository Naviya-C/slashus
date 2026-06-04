package models

import "time"

type User struct {
	ID				string		`gorm:"type:uuid;primaryKey"`
	FirstName		string		`grom:"size:50;not null"`
	LastName		string		`grom:"size:50;not null"`
	Email			string		`grom:"size:100;not null;unique"`
	PasswordHash	string		`grom:"not null"`
	CreatedAt		time.Time	
	UpdatedAt		time.Time
}