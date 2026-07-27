# ==========================
# Build stage
# ==========================
FROM golang:1.26-alpine AS builder

WORKDIR /app

RUN apk add --no-cache git

# Download dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build \
    -trimpath \
    -ldflags="-s -w" \
    -o api-gateway \
    ./cmd/server

# ==========================
# Runtime stage
# ==========================
FROM alpine:3.22

RUN apk add --no-cache ca-certificates tzdata

# Create non-root user
RUN addgroup -S app && adduser -S app -G app

WORKDIR /app

COPY --from=builder /app/api-gateway .

RUN chown -R app:app /app

USER app

EXPOSE 8080

ENTRYPOINT ["./api-gateway"]