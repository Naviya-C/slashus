package service

import ( 
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64" // Convert random bytes into a URL-safe string
	"encoding/hex" // Convert SHA-256 bytes into a readable hex string
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type JWTService interface {
	GenerateTokenAccess(userID, email string) (string, error)
	GenerateRefreshToken() (raw string, hashed string, err error)
	HashRefreshToken(raw string) string
}

type jwtService struct {
	keys       *KeyManager
	issuer     string
	audience   string
	accessTTL  time.Duration
}

// NewJWTService builds the token issuer.

func NewJWTService(keys *KeyManager, issuer, audience string, accessTTL time.Duration) (JWTService, error) {
	if keys == nil {
		return nil, fmt.Errorf("key manager is required")
	}
	if issuer == "" || audience == "" {
		return nil, fmt.Errorf("issuer and audience are required")
	}
	if accessTTL <= 0 {
		accessTTL = 15 * time.Minute
	}
	return &jwtService{keys: keys, issuer: issuer, audience: audience, accessTTL: accessTTL}, nil
}

// GenerateTokenAccess mints a short-lived RS256 access token.

func (s *jwtService) GenerateTokenAccess(userID, email string) (string, error) {
	now := time.Now()
	claims := jwt.MapClaims{
		"sub":   userID,
		"email": email,
		"iss":   s.issuer,
		"aud":   s.audience,
		"iat":   now.Unix(),
		"nbf":   now.Unix(),
		"exp":   now.Add(s.accessTTL).Unix(),
		"jti":   uuid.NewString(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	token.Header["kid"] = s.keys.KeyID()
	return token.SignedString(s.keys.PrivateKey())
}

// GenerateRefreshToken returns the token to hand the client 
func (s *jwtService) GenerateRefreshToken() (string, string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", "", err
	}
	raw := base64.RawURLEncoding.EncodeToString(b)
	return raw, s.HashRefreshToken(raw), nil
}

// HashRefreshToken maps a presented token to its stored form.
func (s *jwtService) HashRefreshToken(raw string) string {
	sum := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(sum[:])
}
