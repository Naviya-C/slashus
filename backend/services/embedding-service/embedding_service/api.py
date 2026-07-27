"""Thin health-check API for the embedding service.

This service previously had no HTTP surface at all — docker-compose exposed
port 8004 for it, but nothing listened there. Added so Docker/Compose (and
any future load balancer) has something to probe. It does not check Qdrant or
Kafka: a readiness probe that calls out to a dependency turns a brief outage
into a container restart loop.

Run EXACTLY ONE instance of this service (see the Dockerfile's own comment):
the sparse encoder writes a shared vocab file and is single-writer.
"""

from fastapi import FastAPI

app = FastAPI(title="embedding-service")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
