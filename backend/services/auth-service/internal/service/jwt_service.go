// internal/service/jwt_service.go
package service

import (
	"crypto/rand"
	"encoding/hex"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type JWTService interface {
	GenerateTokenAccess(userID string, email string) (string, error)
	GenerateRefreshToken() (string, error)
}

type jwtService struct {
	secretKey     []byte
	expireDuration time.Duration
}

func NewJWTService(secret string) JWTService {
	return &jwtService{
		secretKey:      []byte(secret),
		expireDuration: time.Minute * 15, // Token expires in 15 minutes
	}
}

func (s *jwtService) GenerateTokenAccess(userID string, email string) (string, error) {
	// Create the standard and custom claims
	claims := jwt.MapClaims{
		"sub":   userID,                                 // Subject (User ID)
		"email": email,                                  // Custom data
		"exp":   time.Now().Add(s.expireDuration).Unix(), // Expiration time
		"iat":   time.Now().Unix(),                      // Issued at
	}

	// Create token with HS256 signing method
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	// Sign the token with your secret key
	return token.SignedString(s.secretKey)
}

func (s *jwtService) GenerateRefreshToken() (string, error){
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
        return "", err
    }

	return hex.EncodeToString(b), nil
}