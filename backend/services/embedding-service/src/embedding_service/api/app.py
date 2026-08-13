"""HTTP surface: probes and metrics only.

Search moved to gRPC; this app exists so the orchestrator has something to poll
and so Prometheus has somewhere to scrape. The important change from the
previous version is that ``/health`` is no longer a constant -- it reads the
component registry, so a dead consumer or an unloaded model is visible.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from embedding_service.config.settings import Settings
from embedding_service.observability.health import HealthRegistry


def create_app(*, settings: Settings, health: HealthRegistry) -> FastAPI:
    app = FastAPI(
        title=settings.service_name,
        version=settings.service_version,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
    )

    @app.get("/health/live", tags=["health"])
    async def liveness() -> JSONResponse:
        """Is the process wedged? Dependency outages deliberately do not fail
        this -- restarting on a slow Qdrant only makes the outage worse."""
        alive = health.is_alive
        return JSONResponse(
            status_code=200 if alive else 503,
            content={"status": "alive" if alive else "dead"},
        )

    @app.get("/health/ready", tags=["health"])
    async def readiness() -> JSONResponse:
        ready = health.is_ready
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ready" if ready else "not_ready",
                "components": health.snapshot(),
            },
        )

    @app.get("/health", tags=["health"])
    async def health_compat() -> JSONResponse:
        """Kept so existing probes and compose files do not break on upgrade."""
        return JSONResponse(
            status_code=200 if health.is_ready else 503,
            content={
                "status": "ok" if health.is_ready else "degraded",
                "components": health.snapshot(),
            },
        )

    @app.get("/info", tags=["meta"])
    async def info() -> dict[str, Any]:
        return {
            "service": settings.service_name,
            "version": settings.service_version,
            "environment": settings.environment,
            "collection": settings.qdrant.collection,
            "model": settings.embedding.model_name,
            "dimensions": settings.embedding.dimensions,
            "sparse_buckets": settings.sparse.num_buckets,
        }

    if settings.observability.metrics_enabled:

        @app.get("/metrics", include_in_schema=False)
        async def metrics() -> Response:
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
