package config

import  (
	"testing"
)

func TestLoadEnv(t *testing.T){
	cfg, err := LoadEnv()

	if err != nil {
		t.Fatalf("Load env fails: %v:", err)
	}

	t.Logf("%+v", cfg)
}