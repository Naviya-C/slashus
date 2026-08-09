package service

import (
	"context"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"net/http"
	"sync"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

var (
	ErrInvalidGoogleToken = errors.New("invalid google token")
	ErrEmailNotVerified   = errors.New("google account email is not verified")
)

const (
	googleJWKSURL   = "https://www.googleapis.com/oauth2/v3/certs"
	jwksMinCacheTTL = 10 * time.Minute
	jwksMaxCacheTTL = 24 * time.Hour
)


var googleIssuers = map[string]bool{
	"accounts.google.com":         true,
	"https://accounts.google.com": true,
}

type GoogleClaims struct {
	Sub           string `json:"sub"`
	Email         string `json:"email"`
	EmailVerified bool   `json:"email_verified"`
	GivenName     string `json:"given_name"`
	FamilyName    string `json:"family_name"`
	Name          string `json:"name"`
}

type GoogleVerifier struct {
	clientID string
	client   *http.Client

	mu        sync.RWMutex
	keys      map[string]*rsa.PublicKey
	expiresAt time.Time
}

func NewGoogleVerifier(clientID string) (*GoogleVerifier, error) {
	if clientID == "" {
		return nil, errors.New("GOOGLE_CLIENT_ID is required")
	}
	return &GoogleVerifier{
		clientID: clientID,
		client:   &http.Client{Timeout: 5 * time.Second},
		keys:     map[string]*rsa.PublicKey{},
	}, nil
}

func (g *GoogleVerifier) Verify(ctx context.Context, rawToken string) (*GoogleClaims, error) {
	parsed, err := jwt.Parse(
		rawToken,
		func(t *jwt.Token) (any, error) {
			kid, _ := t.Header["kid"].(string)
			if kid == "" {
				return nil, errors.New("token has no kid")
			}
			return g.keyFor(ctx, kid)
		},

		jwt.WithValidMethods([]string{"RS256"}),
		jwt.WithAudience(g.clientID),
		jwt.WithExpirationRequired(),
		jwt.WithLeeway(30*time.Second),
	)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidGoogleToken, err)
	}

	claims, ok := parsed.Claims.(jwt.MapClaims)
	if !ok || !parsed.Valid {
		return nil, ErrInvalidGoogleToken
	}

	iss, _ := claims["iss"].(string)
	if !googleIssuers[iss] {
		return nil, fmt.Errorf("%w: unexpected issuer %q", ErrInvalidGoogleToken, iss)
	}

	out := &GoogleClaims{}
	out.Sub, _ = claims["sub"].(string)
	out.Email, _ = claims["email"].(string)
	out.EmailVerified, _ = claims["email_verified"].(bool)
	out.GivenName, _ = claims["given_name"].(string)
	out.FamilyName, _ = claims["family_name"].(string)
	out.Name, _ = claims["name"].(string)

	if out.Sub == "" || out.Email == "" {
		return nil, fmt.Errorf("%w: missing sub or email", ErrInvalidGoogleToken)
	}
	if !out.EmailVerified {
		return nil, ErrEmailNotVerified
	}

	return out, nil
}

func (g *GoogleVerifier) keyFor(ctx context.Context, kid string) (*rsa.PublicKey, error) {
	g.mu.RLock()
	key, ok := g.keys[kid]
	fresh := time.Now().Before(g.expiresAt)
	g.mu.RUnlock()

	if ok && fresh {
		return key, nil
	}

	if err := g.refresh(ctx); err != nil {
		if ok {
			return key, nil
		}
		return nil, err
	}

	g.mu.RLock()
	key, ok = g.keys[kid]
	g.mu.RUnlock()
	if !ok {
		return nil, fmt.Errorf("%w: unknown kid %q", ErrInvalidGoogleToken, kid)
	}
	return key, nil
}

type jwksResponse struct {
	Keys []struct {
		Kid string `json:"kid"`
		Kty string `json:"kty"`
		Alg string `json:"alg"`
		Use string `json:"use"`
		N   string `json:"n"`
		E   string `json:"e"`
	} `json:"keys"`
}

func (g *GoogleVerifier) refresh(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, googleJWKSURL, nil)
	if err != nil {
		return err
	}

	resp, err := g.client.Do(req)
	if err != nil {
		return fmt.Errorf("fetch google jwks: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("google jwks returned %d", resp.StatusCode)
	}

	var body jwksResponse
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return fmt.Errorf("decode google jwks: %w", err)
	}

	next := make(map[string]*rsa.PublicKey, len(body.Keys))
	for _, k := range body.Keys {
		if k.Kty != "RSA" || (k.Use != "" && k.Use != "sig") {
			continue
		}
		pub, err := parseRSAPublicKey(k.N, k.E)
		if err != nil {
			continue 
		}
		next[k.Kid] = pub
	}

	if len(next) == 0 {
		return errors.New("google jwks contained no usable RSA keys")
	}

	g.mu.Lock()
	g.keys = next
	g.expiresAt = time.Now().Add(cacheTTL(resp.Header.Get("Cache-Control")))
	g.mu.Unlock()

	return nil
}

func parseRSAPublicKey(nStr, eStr string) (*rsa.PublicKey, error) {
	nBytes, err := base64.RawURLEncoding.DecodeString(nStr)
	if err != nil {
		return nil, err
	}
	eBytes, err := base64.RawURLEncoding.DecodeString(eStr)
	if err != nil {
		return nil, err
	}
	if len(eBytes) == 0 || len(nBytes) == 0 {
		return nil, errors.New("empty modulus or exponent")
	}

	e := new(big.Int).SetBytes(eBytes)
	if !e.IsInt64() || e.Int64() > int64(^uint32(0)>>1) {
		return nil, errors.New("exponent out of range")
	}

	return &rsa.PublicKey{
		N: new(big.Int).SetBytes(nBytes),
		E: int(e.Int64()),
	}, nil
}

func cacheTTL(header string) time.Duration {
	ttl := time.Hour

	var maxAge int
	if _, err := fmt.Sscanf(header, "public, max-age=%d", &maxAge); err == nil && maxAge > 0 {
		ttl = time.Duration(maxAge) * time.Second
	}

	if ttl < jwksMinCacheTTL {
		return jwksMinCacheTTL
	}
	if ttl > jwksMaxCacheTTL {
		return jwksMaxCacheTTL
	}
	return ttl
}