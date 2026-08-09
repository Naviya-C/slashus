package repository

import (
	"errors"

	"auth-service/internal/domain/models"

	"gorm.io/gorm"
)

type PostgresOAuthRepository struct {
	db *gorm.DB
}

func NewPostgresOAuthRepository(db *gorm.DB) *PostgresOAuthRepository {
	return &PostgresOAuthRepository{db: db}
}

func (r *PostgresOAuthRepository) FindByProviderUID(provider, providerUID string) (*models.OAuthAccount, error) {
	var account models.OAuthAccount
	err := r.db.
		Where("provider = ? AND provider_uid = ?", provider, providerUID).
		First(&account).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &account, nil
}

func (r *PostgresOAuthRepository) CreateUserWithOAuth(user *models.User, account *models.OAuthAccount) error {
	return r.db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(user).Error; err != nil {
			return err
		}
		// Set after the insert so the DB-generated UUID is the one used.
		account.UserID = user.ID
		return tx.Create(account).Error
	})
}

func (r *PostgresOAuthRepository) LinkToExistingUser(account *models.OAuthAccount) error {
	err := r.db.Create(account).Error
	if err != nil && isUniqueViolation(err) {
		return nil
	}
	return err
}


func isUniqueViolation(err error) bool {
	if err == nil {
		return false
	}
	msg := err.Error()
	return containsAny(msg, "23505", "duplicate key value", "UNIQUE constraint")
}

func containsAny(s string, subs ...string) bool {
	for _, sub := range subs {
		if len(sub) > 0 && len(s) >= len(sub) && indexOf(s, sub) >= 0 {
			return true
		}
	}
	return false
}

func indexOf(s, sub string) int {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return i
		}
	}
	return -1
}