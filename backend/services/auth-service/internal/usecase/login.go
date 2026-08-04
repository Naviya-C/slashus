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


var (
	ErrInvalidCredentials = errors.New("invalid email or password")
	ErrAccountLocked      = errors.New("too many failed attempts; try again later")
)


const dummyHash = "$argon2id$v=19$m=65536,t=3,p=2$c29tZXJhbmRvbXNhbHQx$Zm9vYmFyYmF6cXV4Y29ycmVjdGhvcnNlYmF0dGVyeQ"

const refreshTTL = 30 * 24 * time.Hour

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

func (l *LoginUseCase) Login(email, password string) (string, string, error) {
	if l.attempts != nil {
		if n, err := l.attempts.Failed(email); err == nil && n >= l.maxAttempts {
			return "", "", ErrAccountLocked
		}
	}

	user, err := l.userRepo.FindByEmail(email)

	if err != nil || user == nil {
		_ = l.passwordService.Verify(password, dummyHash)
		l.recordFailure(email)
		return "", "", ErrInvalidCredentials
	}

	if err := l.passwordService.Verify(password, user.PasswordHash); err != nil {
		l.recordFailure(email)
		return "", "", ErrInvalidCredentials
	}

	if l.attempts != nil {
		_ = l.attempts.Reset(email)
	}

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

	record := &models.RefreshToken{
		UserID:    user.ID,
		TokenHash: hashedRefresh,
		FamilyID:  uuid.New(), 
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
