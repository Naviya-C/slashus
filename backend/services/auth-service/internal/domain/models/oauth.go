package models

import (
	"time"

	"github.com/google/uuid"
)


const (
	ProviderGoogle = "google"
)

type OAuthAccount struct {
	ID          uuid.UUID `gorm:"type:uuid;default:gen_random_uuid();primaryKey"`
	UserID      uuid.UUID `gorm:"type:uuid;not null;index"`
	Provider    string    `gorm:"size:32;not null;uniqueIndex:uq_oauth_provider_uid"`
	ProviderUID string    `gorm:"size:255;not null;uniqueIndex:uq_oauth_provider_uid"`
	Email       string    `gorm:"size:100;not null"`
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

func (OAuthAccount) TableName() string { return "oauth_accounts" }