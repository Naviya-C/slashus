package usecase

import (
	"context"
	"errors"
	"strings"
	"time"

	"auth-service/internal/domain/models"
	"auth-service/internal/domain/repository"
	"auth-service/internal/service"

	"github.com/google/uuid"
)

var (
	ErrEmailHasPassword = errors.New("email already registered with a password")
	ErrGoogleUnavailable = errors.New("could not verify google account")
)

type OAuthRepository interface {
	FindByProviderUID(provider, providerUID string) (*models.OAuthAccount, error)
	CreateUserWithOAuth(user *models.User, account *models.OAuthAccount) error
	LinkToExistingUser(account *models.OAuthAccount) error
}

type GoogleLoginUseCase struct {
	userRepo   repository.UserRepository
	oauthRepo  OAuthRepository
	verifier   *service.GoogleVerifier
	jwtService service.JWTService
	autoLink bool
}

func NewGoogleLoginUseCase(
	userRepo repository.UserRepository,
	oauthRepo OAuthRepository,
	verifier *service.GoogleVerifier,
	jwtService service.JWTService,
	autoLink bool,
) *GoogleLoginUseCase {
	return &GoogleLoginUseCase{
		userRepo:   userRepo,
		oauthRepo:  oauthRepo,
		verifier:   verifier,
		jwtService: jwtService,
		autoLink:   autoLink,
	}
}

func (g *GoogleLoginUseCase) Login(ctx context.Context, idToken string) (string, string, error) {
	claims, err := g.verifier.Verify(ctx, idToken)
	if err != nil {
		return "", "", err
	}

	email := strings.ToLower(strings.TrimSpace(claims.Email))

	user, err := g.resolveUser(claims, email)
	if err != nil {
		return "", "", err
	}

	return g.issueTokens(user)
}


func (g *GoogleLoginUseCase) resolveUser(claims *service.GoogleClaims, email string) (*models.User, error) {
	account, err := g.oauthRepo.FindByProviderUID(models.ProviderGoogle, claims.Sub)
	if err != nil {
		return nil, err
	}
	if account != nil {
		user, err := g.userRepo.FindByID(account.UserID)
		if err != nil {
			return nil, err
		}
		if user == nil {
			return nil, errors.New("oauth account references a missing user")
		}
		return user, nil
	}

	existing, err := g.userRepo.FindByEmail(email)
	if err != nil {
		return nil, err
	}

	if existing != nil {
		hasPassword := existing.PasswordHash != ""
		if hasPassword && !g.autoLink {
			return nil, ErrEmailHasPassword
		}

		link := &models.OAuthAccount{
			UserID:      existing.ID,
			Provider:    models.ProviderGoogle,
			ProviderUID: claims.Sub,
			Email:       email,
		}
		if err := g.oauthRepo.LinkToExistingUser(link); err != nil {
			return nil, err
		}
		return existing, nil
	}

	first, last := splitName(claims)
	newUser := &models.User{
		FirstName: first,
		LastName:  last,
		Email:     email,
		PasswordHash: "",
	}
	newAccount := &models.OAuthAccount{
		Provider:    models.ProviderGoogle,
		ProviderUID: claims.Sub,
		Email:       email,
	}

	if err := g.oauthRepo.CreateUserWithOAuth(newUser, newAccount); err != nil {
		return nil, err
	}
	return newUser, nil
}

func (g *GoogleLoginUseCase) issueTokens(user *models.User) (string, string, error) {
	accessToken, err := g.jwtService.GenerateTokenAccess(user.ID.String(), user.Email)
	if err != nil {
		return "", "", errors.New("failed to generate authentication token")
	}

	rawRefresh, hashedRefresh, err := g.jwtService.GenerateRefreshToken()
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
	if err := g.userRepo.SaveRefreshToken(record); err != nil {
		return "", "", errors.New("failed to secure login session")
	}

	return accessToken, rawRefresh, nil
}


func splitName(c *service.GoogleClaims) (string, string) {
	first := strings.TrimSpace(c.GivenName)
	last := strings.TrimSpace(c.FamilyName)

	if first == "" && last == "" {
		full := strings.Fields(strings.TrimSpace(c.Name))
		switch len(full) {
		case 0:
			return "User", "-"
		case 1:
			return full[0], "-"
		default:
			return full[0], strings.Join(full[1:], " ")
		}
	}
	if first == "" {
		first = last
	}
	if last == "" {
		last = "-"
	}

	return truncate(first, 50), truncate(last, 50)
}


func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}