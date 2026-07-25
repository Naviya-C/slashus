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

var (
	ErrInvalidHash        = errors.New("The encoded hash is not in the correct format")
	ErrPasswordMismatched = errors.New("Password does not match the hash")
	ErrPasswordTooLong    = errors.New("Password exceeds the maximum length")
)

// maxPasswordLen caps input before hashing.
//
// Argon2 cost scales with input size, so an unbounded password is a cheap
// denial-of-service: a few concurrent 10 MB "passwords" will saturate CPU and
// memory. 1 KiB is far beyond any real passphrase.
const maxPasswordLen = 1024

// Current parameters for NEW hashes. Existing hashes are verified with
// whatever parameters THEY were created with — see Verify.
const (
	// These determine how expensive hashing is, higher values -> solwer for attackers.
	argonTime    uint32 = 3
	argonMemory  uint32 = 64 * 1024 // 64 MiB
	argonThreads uint8  = 2
	argonKeyLen  uint32 = 32
	argonSaltLen        = 16
)

type PasswordService interface {
	Hash(password string) (string, error)
	Verify(password, hash string) error
	NeedsRehash(hash string) bool
}

type Argon2idPasswordService struct{}

func NewArgon2idPasswordService() *Argon2idPasswordService {
	return &Argon2idPasswordService{}
}

func (a *Argon2idPasswordService) Hash(password string) (string, error) {
	if len(password) > maxPasswordLen {
		return "", ErrPasswordTooLong
	}

	salt := make([]byte, argonSaltLen)
	if _, err := rand.Read(salt); err != nil {
		return "", err
	}

	hash := argon2.IDKey([]byte(password), salt, argonTime, argonMemory, argonThreads, argonKeyLen)

	return fmt.Sprintf(
		"$argon2id$v=%d$m=%d,t=%d,p=%d$%s$%s", // return PHC string format
		argon2.Version, argonMemory, argonTime, argonThreads,
		base64.RawStdEncoding.EncodeToString(salt),
		base64.RawStdEncoding.EncodeToString(hash),
	), nil
}

// params holds what a stored hash was created with.
type params struct {
	memory  uint32
	time    uint32
	threads uint8
	keyLen  uint32
}

// decode splits a PHC string into its parts.
//
// The parameters are PARSED, not assumed. The previous implementation
// hardcoded t=3, m=64MB, p=2 in Verify — so the moment those constants were
// raised (which you should do as hardware improves), every existing user would
// be locked out, because their stored hashes were built with the old values.
func decode(encoded string) (p params, salt, hash []byte, err error) {
	parts := strings.Split(encoded, "$")
	if len(parts) != 6 || parts[1] != "argon2id" {
		return p, nil, nil, ErrInvalidHash
	}

	var version int
	if _, err := fmt.Sscanf(parts[2], "v=%d", &version); err != nil {
		return p, nil, nil, ErrInvalidHash
	}
	if version != argon2.Version {
		return p, nil, nil, fmt.Errorf("%w: unsupported argon2 version %d", ErrInvalidHash, version)
	}

	if _, err := fmt.Sscanf(parts[3], "m=%d,t=%d,p=%d", &p.memory, &p.time, &p.threads); err != nil {
		return p, nil, nil, ErrInvalidHash
	}

	if salt, err = base64.RawStdEncoding.DecodeString(parts[4]); err != nil { // base64 -> binary
		return p, nil, nil, ErrInvalidHash
	}
	if hash, err = base64.RawStdEncoding.DecodeString(parts[5]); err != nil {
		return p, nil, nil, ErrInvalidHash
	}
	p.keyLen = uint32(len(hash))
	return p, salt, hash, nil
}

func (a *Argon2idPasswordService) Verify(password, encodedHash string) error {
	if len(password) > maxPasswordLen {
		return ErrPasswordTooLong
	}

	p, salt, want, err := decode(encodedHash)
	if err != nil {
		return err
	}

	got := argon2.IDKey([]byte(password), salt, p.time, p.memory, p.threads, p.keyLen)

	// Constant time: a byte-by-byte comparison leaks how much of the hash
	// matched, which is enough to reconstruct it given enough attempts.
	if subtle.ConstantTimeCompare(want, got) == 1 {
		return nil
	}
	return ErrPasswordMismatched
}

// NeedsRehash reports whether a stored hash used weaker parameters than the
// current ones.
//
// Call it after a SUCCESSFUL login — that is the only moment the plaintext is
// available — and silently re-hash. This is how you raise cost parameters over
// time without a forced password reset.
func (a *Argon2idPasswordService) NeedsRehash(encodedHash string) bool {
	p, _, _, err := decode(encodedHash)
	if err != nil {
		return true // unparseable: replace it
	}
	return p.memory < argonMemory || p.time < argonTime || p.threads < argonThreads
}
