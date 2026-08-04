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


func (r *PostgresUserRepository) UpdatePasswordHash(userID uuid.UUID, hash string) error {
	return r.db.Model(&models.User{}).
		Where("id = ?", userID).
		Updates(map[string]any{
			"password_hash": hash,
			"updated_at":    time.Now(),
		}).Error
}

func (r *PostgresUserRepository) SaveRefreshToken(token *models.RefreshToken) error {
	return r.db.Create(token).Error
}

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

func (r *PostgresUserRepository) RevokeFamily(familyID uuid.UUID) error {
	return r.db.Model(&models.RefreshToken{}).
		Where("family_id = ? AND revoked = ?", familyID, false).
		Update("revoked", true).Error
}

func (r *PostgresUserRepository) RevokeAllForUser(userID uuid.UUID) error {
	return r.db.Model(&models.RefreshToken{}).
		Where("user_id = ? AND revoked = ?", userID, false).
		Update("revoked", true).Error
}

func (r *PostgresUserRepository) DeleteExpired() (int64, error) {
	res := r.db.Where("expires_at < ?", time.Now()).Delete(&models.RefreshToken{})
	return res.RowsAffected, res.Error
}