// Package auth verifies tokens issued by the auth service.
//
// THE ONE PLACE THAT VALIDATES
// ----------------------------
// The gateway is the only component that checks a token. Backends trust the
// X-User-Id header instead, which is safe only because they are unreachable
// from outside.
//
// TWO MODES
// ---------
// HS256 (current): gateway and auth share one secret, matching the auth
//                  service as built. Simple, works today.
// RS256 (target):  auth signs with a private key and publishes public keys at
//                  a JWKS endpoint; the gateway holds only the public half.
//
// WHY RS256 IS WORTH MOVING TO
// ----------------------------
// With HS256 the verifying key IS the signing key. The gateway can therefore
// MINT tokens, not just check them — so a gateway compromise means an attacker
// forges a token for any user. The same applies to every future service that
// needs to verify. With RS256 only auth can mint; everyone else can only
// verify.
//
// Switch by setting JWKS_URL instead of JWT_SECRET. No other code changes.
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

// NewHMACVerifier verifies HS256 tokens with a shared secret.
//
// Rejects an empty secret outright. An empty HMAC key is not a weak key — it
// is a publicly known one, so anyone could forge a valid token for any user.
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

// NewJWKSVerifier verifies RS256 tokens against auth's published public keys.
//
// Keys are fetched once and cached, so verification costs no network call and
// auth is never in the hot path. The cache refreshes on an unknown key id, so
// rotation needs no gateway redeploy.
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

// Verify parses and validates a token, returning its claims.
//
// Always enforced: signature, algorithm, expiry, and a non-empty subject.
// Issuer and audience are enforced only when configured — the auth service
// does not emit them yet, and rejecting every token for a missing claim would
// take the product down. Set JWT_ISSUER / JWT_AUDIENCE once auth adds them.
func (v *Verifier) Verify(tokenString string) (*Claims, error) {
	opts := []jwt.ParserOption{
		// Pin the algorithm. Unpinned, a token with alg=none skips signature
		// verification entirely, and an RS256 deployment could be downgraded
		// to HS256 using the public key as the HMAC secret.
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
