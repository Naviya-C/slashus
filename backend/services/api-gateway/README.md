# API Gateway

The only publicly reachable service. Verifies tokens, injects identity, rate
limits, and routes to backends.

```
verify JWT -> inject X-User-Id -> strip Authorization -> route
```

## The trust boundary

Everything behind the gateway trusts `X-User-Id` completely and never sees a
token. That is safe **only** while backends are unreachable from outside.

In `docker-compose.yml`, **only the gateway gets a `ports:` entry.** Publish
upload's or agentic's port and anyone can send `X-User-Id: <victim>` and read
another user's data — the entire identity model collapses with one curl flag.

Three rewrites happen in `middleware/auth.go`, and all three matter:

1. **Delete any inbound `X-User-Id`** — a client must not be able to smuggle
   its own.
2. **Inject `X-User-Id`** from the verified `sub` claim.
3. **Strip `Authorization`** — a compromised backend can't replay a user's
   token against other services.

## What the auth service must provide

The gateway expects three things. If your auth service differs, this is the
integration list:

**1. RS256-signed tokens.** Not HS256. The gateway verifies with auth's public
key locally, so auth is touched only at login and refresh — never in the hot
path of every request. `jwt.WithValidMethods([]string{"RS256"})` pins the
algorithm, which also blocks the classic `alg: none` downgrade attack.

**2. A JWKS endpoint** at `GET /.well-known/jwks.json` publishing the public
keys:

```json
{"keys":[{"kty":"RSA","use":"sig","kid":"key-1","alg":"RS256","n":"...","e":"AQAB"}]}
```

Fetched once at startup and cached; the cache refreshes on an interval and on
seeing an unknown `kid`, so **key rotation needs no gateway redeploy**.

**3. These claims:**

| Claim | Required | Use |
|---|---|---|
| `sub` | yes | becomes `X-User-Id` — must be the user's UUID |
| `iss` | yes | must match `JWT_ISSUER` |
| `aud` | yes | must match `JWT_AUDIENCE` |
| `exp` | yes | expiry is enforced |
| `email` | no | forwarded as `X-User-Email` |
| `roles` | no | parsed, available for future authorization |

Verifying the signature alone is not enough — `iss` and `aud` are checked
because a token minted by the same auth server for a *different* application
would otherwise be accepted here.

## Routes

| Route | Auth | Backend |
|---|---|---|
| `GET /health` | public | gateway itself |
| `POST /auth/login\|register\|refresh` | public | auth |
| `GET /auth/.well-known/jwks.json` | public | auth |
| `GET /auth/me`, `POST /auth/logout` | protected | auth |
| `POST /uploads` | protected, 10/hr | upload |
| `GET /jobs/{id}` | protected | ingestion |
| `POST /chat`, `/mark`, `GET /history` | protected | agentic |

Public routes are listed **individually**, not as an `/auth/*` wildcard — so a
future admin route on the auth service isn't accidentally exposed.

## Rate limiting

Keyed on **user id, not IP**. A whole school behind one NAT shares an address;
throttling by IP would make one student's activity block everyone else.

Counters live in Redis so limits hold across gateway replicas — an in-process
counter silently doubles the effective limit the moment you run two instances.

**Fails open.** If Redis is down the request is allowed and the error logged.
Failing closed would take the product offline to enforce a cost control.

## Frontend flow (login → dashboard)

```
1. POST /auth/login {email, password}   -> {access_token, refresh_token}
2. store the access token in memory (not localStorage — XSS reads it)
   store the refresh token in an httpOnly cookie
3. redirect to /dashboard
4. every API call: Authorization: Bearer <access_token>
5. on 401: POST /auth/refresh -> new access token -> retry once
6. refresh also fails -> clear state, back to login
```

Access tokens should be short (~15 min) and refresh tokens long (~7 days). The
gateway enforces expiry, so a revoked or stale token stops working at the edge
without any backend involvement.

## Rolling out services one at a time

A backend that isn't deployed returns a clean **502** on its routes while
everything else keeps working (`proxy.ErrorHandler`). So you can deploy
gateway + auth first, verify login end to end, then add upload, then ingestion,
then agentic — with a working system at every step.

## Run

```bash
cp .env.example .env
go mod tidy
go run ./cmd/server

# public
curl localhost:8080/health

# protected without a token -> 401, never reaches a backend
curl -i localhost:8080/chat -X POST -d '{}'

# with a token
curl -X POST localhost:8080/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"hello","session_id":"s1"}'
```

## Verify the boundary holds

The one test worth running before you ship:

```bash
# forged header, no token -> must be 401, NOT proxied
curl -i localhost:8080/chat -X POST \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000000" \
  -d '{"message":"hi"}'
```

If that returns anything other than 401, the identity model is broken.
