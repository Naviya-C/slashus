package repository

import (
	"errors"
	"time"

	"auth-service/internal/domain/models"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type PostgresUserRepository struct {
	db *gorm.DB
}

func NewPostgresUserRepository(db *gorm.DB) *PostgresUserRepository {
	return &PostgresUserRepository{db: db}
}

func (r *PostgresUserRepository) Create(user *models.User) error {
	return r.db.Create(user).Error
}

func (r *PostgresUserRepository) FindByEmail(email string) (*models.User, error) {
	var user models.User
	if err := r.db.Where("email = ?", email).First(&user).Error; err != nil {
		// Not-found is not an error: it is a normal outcome of a login
		// attempt. Callers must therefore check for a nil user, not just a
		// nil error.
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &user, nil
} 

func (r *PostgresUserRepository) FindByID(id uuid.UUID) (*models.User, error) {
	var user models.User
	if err := r.db.First(&user, "id = ?", id).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &user, nil
}

// UpdatePasswordHash writes a new hash, used both for password changes and for
// the opportunistic rehash after a successful login when cost parameters have
// been raised.
func (r *PostgresUserRepository) UpdatePasswordHash(userID uuid.UUID, hash string) error {
	return r.db.Model(&models.User{}).
		Where("id = ?", userID).
		Updates(map[string]any{
			"password_hash": hash,
			"updated_at":    time.Now(),
		}).Error
}

// --- refresh tokens --------------------------------------------------------
//
// Every method below takes a HASH. The raw token is never stored and therefore
// never queried; passing a raw value here would simply find nothing.

func (r *PostgresUserRepository) SaveRefreshToken(token *models.RefreshToken) error {
	return r.db.Create(token).Error
}

// FindUserByRefreshTokenHash returns the token row AND its owner.
//
// Deliberately returns revoked and expired rows rather than filtering them
// out: the refresh use case must be able to SEE a revoked token, because that
// is exactly what reuse detection keys on. Filtering here would make a stolen
// token indistinguishable from an unknown one.
func (r *PostgresUserRepository) FindUserByRefreshTokenHash(hash string) (*models.User, *models.RefreshToken, error) {
	var record models.RefreshToken
	if err := r.db.Where("token_hash = ?", hash).First(&record).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil, nil
		}
		return nil, nil, err
	}

	var user models.User
	if err := r.db.First(&user, "id = ?", record.UserID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil, nil
		}
		return nil, nil, err
	}
	return &user, &record, nil
}

// RotateRefreshToken retires oldHash and inserts next, atomically.
//
// WHY A TRANSACTION
// -----------------
// Split into two calls, a crash between them either revokes the old token
// without issuing a new one (user locked out) or issues a new one while the
// old stays live (two valid tokens, defeating reuse detection).
//
// WHY THE ROWS-AFFECTED CHECK
// ---------------------------
// The UPDATE is conditional on `revoked = false`, and we require it to touch
// exactly one row. If two requests present the same token concurrently, only
// the first sees revoked = false; the second gets 0 rows and aborts. Without
// this, both would succeed and mint two live tokens from one — silently
// creating the situation reuse detection exists to catch.
func (r *PostgresUserRepository) RotateRefreshToken(oldHash string, next *models.RefreshToken) error {
	return r.db.Transaction(func(tx *gorm.DB) error {
		now := time.Now()

		res := tx.Model(&models.RefreshToken{}).
			Where("token_hash = ? AND revoked = ?", oldHash, false).
			Updates(map[string]any{
				"revoked":    true,
				"rotated_at": now,
			})
		if res.Error != nil {
			return res.Error
		}
		if res.RowsAffected != 1 {
			// Already rotated by a concurrent request, or gone.
			return errors.New("refresh token is no longer valid")
		}

		return tx.Create(next).Error
	})
}

func (r *PostgresUserRepository) RevokeRefreshToken(hash string) error {
	return r.db.Model(&models.RefreshToken{}).
		Where("token_hash = ?", hash).
		Update("revoked", true).Error
}

// RevokeFamily kills every token descended from one login.
//
// Runs on logout and, critically, on reuse detection: if a used token comes
// back, two parties hold it and we cannot tell which is legitimate, so the
// whole chain goes.
func (r *PostgresUserRepository) RevokeFamily(familyID uuid.UUID) error {
	return r.db.Model(&models.RefreshToken{}).
		Where("family_id = ? AND revoked = ?", familyID, false).
		Update("revoked", true).Error
}

// RevokeAllForUser is "sign out everywhere" — the correct response to a
// password change or a suspected compromise.
func (r *PostgresUserRepository) RevokeAllForUser(userID uuid.UUID) error {
	return r.db.Model(&models.RefreshToken{}).
		Where("user_id = ? AND revoked = ?", userID, false).
		Update("revoked", true).Error
}

// DeleteExpired prunes rows past expiry. Run it on a schedule — without it the
// table grows forever, and the unique index on token_hash grows with it.
//
// Revoked-but-unexpired rows are kept on purpose: they are what reuse
// detection matches against. Delete them early and a stolen token looks merely
// unknown instead of stolen.
func (r *PostgresUserRepository) DeleteExpired() (int64, error) {
	res := r.db.Where("expires_at < ?", time.Now()).Delete(&models.RefreshToken{})
	return res.RowsAffected, res.Error
}