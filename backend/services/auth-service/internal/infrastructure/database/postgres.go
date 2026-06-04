package database

import (
	"auth-service/internal/config"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func connect(cfg *config.Config)(*gorm.DB, error){
	return gorm.Open(
		postgres.Open(cfg.DatabaseURL_P),
		&gorm.Config{},
	)
}

