package auth

import (
	"context"
	"fmt"

	"github.com/MicahParks/keyfunc/v3"
	"github.com/golang-jwt/jwt/v5"
)

type Verifier struct {
	// exactly one of these is set
	secret []byte
	jwks   keyfunc.Keyfunc

	methods  []string
	issuer   string // optional; checked only when non-empty
	audience string // optional; checked only when non-empty
}

// Claims is the subset the gateway needs. `sub` becomes X-User-Id.
type Claims struct {
	UserID string
	Email  string
	Roles  []string
}
func NewHMACVerifier(secret, issuer, audience string) (*Verifier, error) {
	if secret == "" {
		return nil, fmt.Errorf("JWT_SECRET is empty; refusing to start")
	}
	if len(secret) < 32 {
		return nil, fmt.Errorf("JWT_SECRET is too short (%d bytes); use at least 32", len(secret))
	}
	return &Verifier{
		secret:   []byte(secret),
		methods:  []string{"HS256"},
		issuer:   issuer,
		audience: audience,
	}, nil
}
func NewJWKSVerifier(ctx context.Context, jwksURL, issuer, audience string) (*Verifier, error) {
	jwks, err := keyfunc.NewDefaultCtx(ctx, []string{jwksURL})
	if err != nil {
		return nil, fmt.Errorf("fetching jwks from %s: %w", jwksURL, err)
	}
	return &Verifier{
		jwks:     jwks,
		methods:  []string{"RS256"},
		issuer:   issuer,
		audience: audience,
	}, nil
}

func (v *Verifier) keyfunc(token *jwt.Token) (any, error) {
	if v.jwks != nil {
		return v.jwks.Keyfunc(token)
	}
	return v.secret, nil
}
func (v *Verifier) Verify(tokenString string) (*Claims, error) {
	opts := []jwt.ParserOption{
		jwt.WithValidMethods(v.methods),
		jwt.WithExpirationRequired(),
	}
	if v.issuer != "" {
		opts = append(opts, jwt.WithIssuer(v.issuer))
	}
	if v.audience != "" {
		opts = append(opts, jwt.WithAudience(v.audience))
	}

	token, err := jwt.Parse(tokenString, v.keyfunc, opts...)
	if err != nil {
		return nil, fmt.Errorf("invalid token: %w", err)
	}
	if !token.Valid {
		return nil, fmt.Errorf("token is not valid")
	}

	mapClaims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return nil, fmt.Errorf("unexpected claims type")
	}

	sub, _ := mapClaims["sub"].(string)
	if sub == "" {
		return nil, fmt.Errorf("token has no subject")
	}

	claims := &Claims{UserID: sub}
	if email, ok := mapClaims["email"].(string); ok {
		claims.Email = email
	}
	if raw, ok := mapClaims["roles"].([]any); ok {
		for _, r := range raw {
			if s, ok := r.(string); ok {
				claims.Roles = append(claims.Roles, s)
			}
		}
	}
	return claims, nil
}
