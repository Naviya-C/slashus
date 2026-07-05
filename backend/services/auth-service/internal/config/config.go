package config

import (
	"fmt"
	"os"

	"github.com/joho/godotenv"
)

type Config struct{
	DatabaseURL		string
	DatabaseURL_P	string
	JWTService string
}

func LoadEnv()(*Config, error){
	_ = godotenv.Load()

	cgf := &Config{
		DatabaseURL: os.Getenv("DATABASE_URL"),
		DatabaseURL_P: os.Getenv("DATABASE_URL_P"),
		JWTService: os.Getenv("JWT_SECRET"),
	}

	if cgf.DatabaseURL == "" {
		return nil, fmt.Errorf("Database URL is not founded")
	}
	if cgf.DatabaseURL_P == "" {
		return nil, fmt.Errorf("Pooling Database Url is not founded")
	}

	return cgf, nil
}