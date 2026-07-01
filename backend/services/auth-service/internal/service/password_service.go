package service

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"errors"
	"fmt"
	"strings"

	"golang.org/x/crypto/argon2"
)

var ErrInvalidHash = errors.New("the encoded hash is not in the correct format")
var ErrPasswordMismatched = errors.New("password does not match the hash")

type PasswordService interface {
	Hash(password string) (string, error)
	Verify(password, hash string) error
}

type Argon2idPasswordService struct{}

func NewArgon2idPasswordService() *Argon2idPasswordService {
	return &Argon2idPasswordService{}
}

func (a *Argon2idPasswordService) Hash(password string) (string, error) {
	// Generate Random Salt
	salt := make([]byte, 16)
	_, err := rand.Read(salt)
	if err != nil {
		return "", err
	}

	// Generate argon hash
	// Parameters: time=3, memory=64MB, threads=2, keyLen=32
	hash := argon2.IDKey([]byte(password), salt, 3, 64*1024, 2, 32)

	saltEncoder := base64.RawStdEncoding.EncodeToString(salt)
	hashEncoder := base64.RawStdEncoding.EncodeToString(hash)

	encodedHash := fmt.Sprintf(
		"$argon2id$v=19$m=65536,t=3,p=2$%s$%s",
		saltEncoder,
		hashEncoder,
	)

	return encodedHash, nil
}

// Verify decodes the saved hash to extract the salt and parameters, re-hashes 
// the incoming password, and compares them using a constant-time comparison.
func (a *Argon2idPasswordService) Verify(password, encodedHash string) error {
	// Split the PHC string format: ["", "argon2id", "v=19", "m=65536,t=3,p=2", salt, hash]
	parts := strings.Split(encodedHash, "$")
	if len(parts) != 6 {
		return ErrInvalidHash
	}

	salt, err := base64.RawStdEncoding.DecodeString(parts[4])
	if err != nil {
		return err
	}

	originalHash, err := base64.RawStdEncoding.DecodeString(parts[5])
	if err != nil {
		return err
	}

	// Re-hash the input password using the exact same extracted salt and parameters
	comparisonHash := argon2.IDKey([]byte(password), salt, 3, 64*1024, 2, 32)

	// Use subtle.ConstantTimeCompare to prevent timing attacks
	if subtle.ConstantTimeCompare(originalHash, comparisonHash) == 1 {
		return nil
	}

	return ErrPasswordMismatched
}