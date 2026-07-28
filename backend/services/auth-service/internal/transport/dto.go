package transport

import (
	"time"
	"github.com/google/uuid"
)

type RegisterRequest struct {
	FirstName string `json:"firstName"`
	LastName  string `json:"lastName"`
	Email     string `json:"email"`
	Password  string `json:"password"`
}

type LoginRequest struct {
	Email		string `json:"email"`
	Password	string `json:"password"`
}

type UserMe struct {
	UserId uuid.UUID `json:"userid"`
	FirstName string `json:"firstName"`
	LastName  string `json:"lastName"`
	Email     string `json:"email"`
	CreatedAt time.Time `json:"createdAt"`
}