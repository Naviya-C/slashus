package models

import (
	"time"
	"github.com/google/uuid"
)

type RefreshToken struct {
	ID        uuid.UUID  `gorm:"type:uuid;default:gen_random_uuid();primaryKey"`
	UserID    uuid.UUID  `gorm:"type:uuid;not null;index"`
	FamilyID  uuid.UUID  `gorm:"type:uuid;not null;index"`
	TokenHash string     `gorm:"type:text;not null;uniqueIndex"`
	ExpiresAt time.Time  `gorm:"not null"`
	Revoked   bool       `gorm:"default:false"`
	RotatedAt *time.Time `gorm:"type:timestamptz"`
	CreatedAt time.Time  `gorm:"autoCreateTime"`

	User User `gorm:"foreignKey:UserID;constraint:OnDelete:CASCADE"`
}