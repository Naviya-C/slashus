// internal/usecase/logout.go
package usecase

import (
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"

	"github.com/google/uuid"
)

type LogoutUseCase struct {
	userRepo   repository.UserRepository
	jwtService service.JWTService
}

func NewLogoutUseCase(userRepo repository.UserRepository, jwtService service.JWTService) *LogoutUseCase {
	return &LogoutUseCase{userRepo: userRepo, jwtService: jwtService}
}

// Logout revokes the presented refresh token's whole family, ending that
// session everywhere it was rotated to.
//
// WHY THE FAMILY AND NOT JUST THE TOKEN
// -------------------------------------
// Rotation means one login produces a chain of refresh tokens. Revoking only
// the token the client happens to be holding would leave earlier links in the
// chain usable if a copy leaked. Revoking the family ends the session in one
// operation.
//
// Returns nil even when the token is unknown: logout must be idempotent. A
// client retrying after a network blip should not see an error, and reporting
// "no such token" would let an attacker probe which tokens are live.
func (u *LogoutUseCase) Logout(presentedRefreshToken string) error {
	hashed := u.jwtService.HashRefreshToken(presentedRefreshToken)

	_, record, err := u.userRepo.FindUserByRefreshTokenHash(hashed)
	if err != nil || record == nil {
		return nil
	}
	return u.userRepo.RevokeFamily(record.FamilyID)
}

// LogoutAll revokes every refresh token for a user — "sign out of all
// devices", and the correct response to a password change or a suspected
// compromise.
//
// Note the access-token caveat: already-issued access tokens stay valid until
// they expire, because verification is stateless by design. That is why the
// access TTL is short (15 minutes). If you need instant revocation, add a
// denylist of `jti` values checked at the gateway — at the cost of a lookup on
// every request.
func (u *LogoutUseCase) LogoutAll(userID uuid.UUID) error {
	return u.userRepo.RevokeAllForUser(userID)
}
