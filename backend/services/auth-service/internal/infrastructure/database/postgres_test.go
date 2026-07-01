package database

import (
    "testing"

    "auth-service/internal/config"
)

func TestPostgresConnection(t *testing.T){

	cfg, err := config.LoadEnv()

	if err != nil{
		t.Fatalf("%v", err)
	}

	db_connect, err := Connect(cfg)

	if err != nil {
		t.Fatalf("failed to connect database: %v", err)
	}

	if db_connect == nil{
		t.Fatalf("failed to connect database")
	}
}