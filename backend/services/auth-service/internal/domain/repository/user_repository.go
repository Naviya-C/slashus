// internal/domain/repository/user_repository.go
package repository

import (
	"auth-service/internal/domain/models"

	"github.com/google/uuid"
)

// UserRepository is the persistence contract.
//
// Every refresh-token method takes a HASH, never a raw token. Making that
// explicit in the interface means a caller cannot accidentally pass the raw
// value and reintroduce plaintext storage — which is exactly how the original
// bug happened.
type UserRepository interface {
	Create(user *models.User) error
	FindByEmail(email string) (*models.User, error)
	FindByID(id uuid.UUID) (*models.User, error)
	UpdatePasswordHash(userID uuid.UUID, hash string) error

	// --- refresh tokens ---
	SaveRefreshToken(token *models.RefreshToken) error
	FindUserByRefreshTokenHash(hash string) (*models.User, *models.RefreshToken, error)

	// RotateRefreshToken revokes oldHash and inserts next in ONE transaction.
	// Two separate calls leave a window where a crash either locks the user
	// out or leaves two live tokens.
	RotateRefreshToken(oldHash string, next *models.RefreshToken) error

	RevokeRefreshToken(hash string) error

	// RevokeFamily kills every token descended from one login. Used on logout
	// and, critically, on reuse detection.
	RevokeFamily(familyID uuid.UUID) error

	RevokeAllForUser(userID uuid.UUID) error

	// DeleteExpired prunes rows past expiry; run on a schedule so the table
	// does not grow without bound.
	DeleteExpired() (int64, error)
}
