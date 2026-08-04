package service
/*
single responsibility of this file is:
	- Load or generate RSA keys.
	- Validate that the keys are suitable for production (at least 2048 bits).
	- Compute a stable kid.
	- Provide access to the private key for signing.
	- Expose the public key in JWKS format so other services can verify JWTs.
*/

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/binary"
	"encoding/pem"
	"fmt"
	"math/big"
	"os"
)

type KeyManager struct {
	private *rsa.PrivateKey
	kid     string
}

func NewKeyManagerFromPEM(pemData []byte) (*KeyManager, error) {
	block, _ := pem.Decode(pemData)
	if block == nil {
		return nil, fmt.Errorf("no PEM block found in private key")
	}

	var key *rsa.PrivateKey
	switch block.Type {
		case "RSA PRIVATE KEY":
			k, err := x509.ParsePKCS1PrivateKey(block.Bytes)
			if err != nil {
				return nil, fmt.Errorf("parsing PKCS#1 key: %w", err)
			}
			key = k
		case "PRIVATE KEY":
			parsed, err := x509.ParsePKCS8PrivateKey(block.Bytes)
			if err != nil {
				return nil, fmt.Errorf("parsing PKCS#8 key: %w", err)
			}
			k, ok := parsed.(*rsa.PrivateKey) // ParsePKCS8PrivateKey returns interface, the type don't know but in here expecting RSA.
			if !ok {
				return nil, fmt.Errorf("key is not RSA")
			}
			key = k
		default:
			return nil, fmt.Errorf("unsupported PEM block type %q", block.Type)
	}

	if key.N.BitLen() < 2048 {
		return nil, fmt.Errorf("RSA key is %d bits; use at least 2048", key.N.BitLen())
	}

	return &KeyManager{private: key, kid: thumbprint(&key.PublicKey)}, nil
}

func LoadKeyManager() (*KeyManager, error) {
	if pemStr := os.Getenv("JWT_PRIVATE_KEY"); pemStr != "" {
		return NewKeyManagerFromPEM([]byte(pemStr))
	}
	if path := os.Getenv("JWT_PRIVATE_KEY_FILE"); path != "" {
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("reading %s: %w", path, err)
		}
		return NewKeyManagerFromPEM(data)
	}
	return nil, fmt.Errorf("set JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_FILE")
}

func GenerateDevKey() (*KeyManager, error) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, err
	}
	return &KeyManager{private: key, kid: thumbprint(&key.PublicKey)}, nil
}

func (k *KeyManager) PrivateKey() *rsa.PrivateKey { return k.private }
func (k *KeyManager) KeyID() string               { return k.kid }

// JWKS returns the public key set served at /.well-known/jwks.json.
func (k *KeyManager) JWKS() map[string]any {
	pub := k.private.PublicKey

	eBytes := make([]byte, 8)
	binary.BigEndian.PutUint64(eBytes, uint64(pub.E)) // Converts integer into bytes
	// trim leading zero bytes — JWK wants the minimal big-endian encoding
	i := 0
	for i < len(eBytes)-1 && eBytes[i] == 0 {
		// Removing leading zeros.
		i++
	}

	return map[string]any{
		"keys": []map[string]string{{
			"kty": "RSA",
			"use": "sig",
			"alg": "RS256",
			"kid": k.kid,
			"n":   base64.RawURLEncoding.EncodeToString(pub.N.Bytes()),
			"e":   base64.RawURLEncoding.EncodeToString(eBytes[i:]),
		}},
	}
}

func thumbprint(pub *rsa.PublicKey) string {
	eBytes := big.NewInt(int64(pub.E)).Bytes()
	canonical := fmt.Sprintf(`{"e":"%s","kty":"RSA","n":"%s"}`,
		base64.RawURLEncoding.EncodeToString(eBytes), // Convert binary into URL safe string
		base64.RawURLEncoding.EncodeToString(pub.N.Bytes()),
	)
	sum := sha256.Sum256([]byte(canonical))
	return base64.RawURLEncoding.EncodeToString(sum[:])
}
