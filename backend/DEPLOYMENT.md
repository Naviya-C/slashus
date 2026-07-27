# Deploying the Slashus backend to a GCP VM, connected to a Vercel frontend

## 1. Create the VM

- Machine type: **e2-standard-2** (2 vCPU, 8 GB RAM) minimum. The embedding
  service alone pulls in CPU torch + sentence-transformers; add Kafka + Redis
  + 4 more containers and 4 GB will swap constantly.
- Image: Ubuntu 24.04 LTS.
- Disk: 30 GB+ (Kafka logs, HF model cache, and uploaded files under `./data/`
  all live on this disk unless you move them to GCS).
- Reserve a **static external IP** (VPC network → IP addresses → reserve),
  so it doesn't change on reboot and you can point DNS at it.

## 2. Firewall

Only the gateway needs to be reachable from the internet.

- Allow: TCP 22 (SSH, ideally from your IP only), TCP 443, TCP 80 (for
  Certbot/Caddy's ACME challenge).
- Do **not** create firewall rules for 8081 (auth), 8002 (upload), 8003
  (ingestion), 6379 (redis), 9092 (kafka). The compose file already doesn't
  publish these to the host; the firewall is a second layer, not the first.

## 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker compose version   # confirm the compose plugin is present
```

## 4. Get TLS in front of the gateway

Your Vercel frontend is served over HTTPS. A browser will block requests from
an HTTPS page to a plain `http://` API (mixed content) and refresh cookies
marked `Secure` won't be sent over `http://` either. You need TLS on the VM.

Simplest option — Caddy as a reverse proxy in front of api-gateway, with
automatic Let's Encrypt certs. Add this as one more service to
`docker-compose.yml`:

```yaml
  caddy:
    image: caddy:2-alpine
    container_name: caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./data/caddy:/data
    depends_on:
      - api-gateway
    restart: unless-stopped
```

And a `Caddyfile`:

```
api.yourdomain.com {
    reverse_proxy api-gateway:8080
}
```

Then change api-gateway's compose entry from `ports: ["8080:8080"]` to
`expose: ["8080"]` — Caddy is now the only thing publishing a host port.
Point an A record for `api.yourdomain.com` at the VM's static IP.

## 5. Ship the code and secrets

```bash
# from your machine
scp -r ./slashus-backend you@VM_IP:~/slashus-backend
```

On the VM, fill in the real `.env` files from the `.env.example` templates —
**do not** commit real secrets to git. The Gemini key, Qdrant token, and Neon
connection string that were in the zip you sent me are real, live credentials;
rotate all three before using them anywhere, since they've now passed through
this chat.

## 6. Bring it up

```bash
cd ~/slashus-backend
docker compose up -d --build
docker compose ps
docker compose logs -f api-gateway   # confirm it actually stays up
```

If `api-gateway` restarts in a loop, check `REDIS_URL` and the three backend
URLs first — those were the two classes of bug that broke boot and routing
in the version you sent (see the errors list above).

## 7. Connect the Vercel frontend

**Domain choice matters more than it looks like here.** The auth service sets
its refresh-token cookie with `SameSite=Strict`. Strict cookies are **not**
sent on cross-site requests — and "site" is judged by registrable domain
(eTLD+1), not by scheme or subdomain. Concretely:

- Frontend on `your-app.vercel.app` + backend on `api.yourdomain.com` →
  **different sites** → the browser will silently drop the refresh cookie on
  every cross-origin call, and refresh/logout will never work, no matter how
  correct the CORS config is.
- Frontend on a **custom domain** `app.yourdomain.com` (via Vercel's custom
  domain feature) + backend on `api.yourdomain.com` → **same site** (both are
  `yourdomain.com`) → `SameSite=Strict` keeps working, and you keep the CSRF
  protection that mode is there for.

So: add a custom domain to your Vercel project rather than relying on the
`*.vercel.app` one, and put the backend on a subdomain of that same domain.

Steps:
1. In Vercel → Project → Settings → Domains, add `app.yourdomain.com`.
2. Point its DNS record (CNAME, per Vercel's instructions) accordingly.
3. Set `api.yourdomain.com` to the VM's static IP (A record).
4. In `services/api-gateway/.env` on the VM, set:
   `CORS_ORIGINS=https://app.yourdomain.com`
5. In the Vercel project's environment variables, set your API base URL:
   `NEXT_PUBLIC_API_URL=https://api.yourdomain.com` (adjust the var name to
   whatever your frontend actually reads).
6. Frontend fetch calls to auth endpoints need `credentials: "include"` so the
   refresh cookie is sent/received at all — confirm this is set wherever the
   frontend calls `/api/v1/auth/*`.
7. Redeploy the Vercel project so the new env var is picked up, restart
   `api-gateway` on the VM so the new `CORS_ORIGINS` is picked up.

## 8. Smoke test

```bash
curl https://api.yourdomain.com/health
curl -X POST https://api.yourdomain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"..."}'
```

Then from the deployed frontend, run through register → login → an
authenticated call → refresh → logout, and watch
`docker compose logs -f api-gateway auth-service` on the VM while you do it.

## 9. Known gaps to close before this is a real production deploy

- `ingestion-service`'s HTTP API (`src/ingestion/api/`) is an empty stub —
  `GET /jobs/{id}` will 502 until it's implemented.
- `embedding-service` has no HTTP surface at all — no health endpoint for
  Docker/Compose or a load balancer to probe.
- `auth-service`'s Redis-backed login-attempt limiter is unimplemented
  (`internal/infrastructure/redis/redis.go` is an empty file) — login is
  currently unlimited-attempt.
- `DEV_MODE=true` regenerates the signing key on every restart — every logged
  in user is signed out on every deploy. Fine for now, not fine long-term.
- The `agentic` (RAG/chat) service referenced by the gateway isn't part of
  this bundle — `/chat`, `/mark`, `/history` will 502 until it's built and
  added to `docker-compose.yml`.
