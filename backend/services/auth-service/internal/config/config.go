package config

import (
	"fmt"
	"os"

	"github.com/joho/godotenv"
)

type config struct{
	DatabaseURL		string
	DatabaseURL_P	string
}

func load_env()(*config, error){
	_ = godotenv.Load()

	cgf := &config{
		DatabaseURL: os.Getenv("DATABASE_URL"),
		DatabaseURL_P: os.Getenv("DATABASE_URL_P"),
	}

	if cgf.DatabaseURL == "" {
		return nil, fmt.Errorf("Database URL is not founded")
	}
	if cgf.DatabaseURL_P == "" {
		return nil, fmt.Errorf("Pooling Database Url is not founded")
	}

	return cgf, nil
}