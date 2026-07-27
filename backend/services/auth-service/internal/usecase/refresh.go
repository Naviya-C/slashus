// internal/usecase/refresh.go
package usecase

import (
	"errors"
	"log/slog"
	"time"

	"auth-service/internal/domain/models"
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"
)

var ErrInvalidRefreshToken = errors.New("invalid or expired refresh token")

type RefreshUseCase struct {
	userRepo   repository.UserRepository
	jwtService service.JWTService
	log        *slog.Logger
}

func NewRefreshUseCase(
	userRepo repository.UserRepository,
	jwtService service.JWTService,
	log *slog.Logger,
) *RefreshUseCase {
	return &RefreshUseCase{userRepo: userRepo, jwtService: jwtService, log: log}
}

// RefreshToken exchanges a refresh token for a NEW access token AND a NEW
// refresh token, invalidating the one presented.
//
// ROTATION + REUSE DETECTION
// --------------------------
// The previous version returned a fresh access token but left the refresh
// token valid for its full 45-day life. A token stolen from a browser, a
// backup, or a log therefore granted an attacker indefinite access, and its
// use was indistinguishable from the real user's.
//
// With rotation, each refresh token is single-use. If a token that has ALREADY
// been used comes back, exactly one thing can be true: two parties hold it, so
// one of them stole it. We cannot tell which — so the safe response is to
// revoke the entire family, logging both out and forcing a real login.
//
// This is the OAuth 2.0 Security BCP recommendation for public clients, and it
// is what turns a silent, permanent compromise into a single failed request
// the user notices.
func (u *RefreshUseCase) RefreshToken(presented string) (accessToken, newRefresh string, err error) {
	// Look up by HASH — the raw token is never stored, so it is never queried.
	hashed := u.jwtService.HashRefreshToken(presented)

	user, record, err := u.userRepo.FindUserByRefreshTokenHash(hashed)
	if err != nil || record == nil || user == nil {
		return "", "", ErrInvalidRefreshToken
	}

	// REUSE DETECTED. This token was already exchanged, so a copy exists
	// somewhere it should not. Kill every token in the family.
	if record.Revoked {
		u.log.Warn("refresh token reuse detected; revoking family",
			"user_id", user.ID, "family_id", record.FamilyID)
		if err := u.userRepo.RevokeFamily(record.FamilyID); err != nil {
			u.log.Error("failed to revoke token family", "err", err)
		}
		return "", "", ErrInvalidRefreshToken
	}

	if time.Now().After(record.ExpiresAt) {
		_ = u.userRepo.RevokeRefreshToken(hashed)
		return "", "", ErrInvalidRefreshToken
	}

	rawNext, hashedNext, err := u.jwtService.GenerateRefreshToken()
	if err != nil {
		return "", "", errors.New("failed to generate refresh token")
	}

	next := &models.RefreshToken{
		UserID: user.ID,
		// Same family: this is a continuation of one login session, so reuse
		// of ANY token in the chain invalidates the whole chain.
		FamilyID:  record.FamilyID,
		TokenHash: hashedNext,
		ExpiresAt: record.ExpiresAt, // do NOT extend; the session still ages out
		Revoked:   false,
		CreatedAt: time.Now(),
	}

	// Rotate atomically: mark the old one used and insert the new one in one
	// transaction. Split across two calls, a crash between them either leaves
	// the user unable to refresh or leaves two live tokens.
	if err := u.userRepo.RotateRefreshToken(hashed, next); err != nil {
		return "", "", errors.New("failed to rotate refresh token")
	}

	accessToken, err = u.jwtService.GenerateTokenAccess(user.ID.String(), user.Email)
	if err != nil {
		return "", "", errors.New("failed to generate access token")
	}

	return accessToken, rawNext, nil
}
