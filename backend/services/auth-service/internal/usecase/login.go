// internal/usecase/login.go
package usecase

import (
	"errors"
	"time"

	"auth-service/internal/domain/models"
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"

	"github.com/google/uuid"
)

// ErrInvalidCredentials is returned for BOTH "no such user" and "wrong
// password".
//
// Distinct messages ("User Not Registered" vs "invalid email or password") let
// anyone enumerate your user base one request at a time — useful for targeted
// phishing and for confirming a breached address is worth attacking. One
// message, always.
var (
	ErrInvalidCredentials = errors.New("invalid email or password")
	ErrAccountLocked      = errors.New("too many failed attempts; try again later")
)

// dummyHash is a real Argon2id hash of a random string, used when the email
// does not exist.
//
// Without it, a missing user returns immediately while an existing user waits
// for Argon2 to run — a timing difference of tens of milliseconds that is
// trivially measurable over a network. Verifying against this constant makes
// both paths cost the same.
const dummyHash = "$argon2id$v=19$m=65536,t=3,p=2$c29tZXJhbmRvbXNhbHQx$Zm9vYmFyYmF6cXV4Y29ycmVjdGhvcnNlYmF0dGVyeQ"

const refreshTTL = 30 * 24 * time.Hour

// LoginAttempts records failed logins so brute force can be slowed.
// Backed by Redis in production so the count survives restarts and is shared
// across replicas.
type LoginAttempts interface {
	Failed(email string) (count int, err error)
	RecordFailure(email string) error
	Reset(email string) error
}

type LoginUseCase struct {
	userRepo        repository.UserRepository
	passwordService service.PasswordService
	jwtService      service.JWTService
	attempts        LoginAttempts
	maxAttempts     int
}

func NewLoginUseCase(
	userRepo repository.UserRepository,
	passwordService service.PasswordService,
	jwtService service.JWTService,
	attempts LoginAttempts,
) *LoginUseCase {
	return &LoginUseCase{
		userRepo:        userRepo,
		passwordService: passwordService,
		jwtService:      jwtService,
		attempts:        attempts,
		maxAttempts:     10,
	}
}

// Login verifies credentials and issues an access + refresh token pair.
func (l *LoginUseCase) Login(email, password string) (string, string, error) {
	// Rate limit before touching the database, so a brute-force run cannot
	// also be used to hammer Postgres.
	if l.attempts != nil {
		if n, err := l.attempts.Failed(email); err == nil && n >= l.maxAttempts {
			return "", "", ErrAccountLocked
		}
	}

	user, err := l.userRepo.FindByEmail(email)

	// `||`, not `&&`. The original condition (err != nil && user == nil) let
	// a (nil, nil) return — which GORM's record-not-found path can produce —
	// fall straight through to user.PasswordHash and panic.
	if err != nil || user == nil {
		// Do the same work as the success path so the response time does not
		// reveal whether the address exists.
		_ = l.passwordService.Verify(password, dummyHash)
		l.recordFailure(email)
		return "", "", ErrInvalidCredentials
	}

	if err := l.passwordService.Verify(password, user.PasswordHash); err != nil {
		l.recordFailure(email)
		return "", "", ErrInvalidCredentials
	}

	// Credentials are good: clear the failure counter.
	if l.attempts != nil {
		_ = l.attempts.Reset(email)
	}

	// Opportunistically upgrade the stored hash if cost parameters have been
	// raised since this password was set. This is the only moment the
	// plaintext is available.
	if l.passwordService.NeedsRehash(user.PasswordHash) {
		if newHash, hErr := l.passwordService.Hash(password); hErr == nil {
			_ = l.userRepo.UpdatePasswordHash(user.ID, newHash)
		}
	}

	accessToken, err := l.jwtService.GenerateTokenAccess(user.ID.String(), user.Email)
	if err != nil {
		return "", "", errors.New("failed to generate authentication token")
	}

	rawRefresh, hashedRefresh, err := l.jwtService.GenerateRefreshToken()
	if err != nil {
		return "", "", errors.New("failed to generate refresh token")
	}

	// Store the HASH, hand the client the raw token. The previous version
	// wrote the raw token into the token_hash column, so a single database
	// read exposed every active session.
	record := &models.RefreshToken{
		UserID:    user.ID,
		TokenHash: hashedRefresh,
		FamilyID:  uuid.New(), // new login = new family; see refresh.go
		ExpiresAt: time.Now().Add(refreshTTL),
		Revoked:   false,
		CreatedAt: time.Now(),
	}
	if err := l.userRepo.SaveRefreshToken(record); err != nil {
		return "", "", errors.New("failed to secure login session")
	}

	return accessToken, rawRefresh, nil
}

func (l *LoginUseCase) recordFailure(email string) {
	if l.attempts != nil {
		_ = l.attempts.RecordFailure(email)
	}
}
