from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ingestion_service.observability.health import HealthRegistry
from ingestion_service.pipeline import JobRepository


def create_app(*, health: HealthRegistry, jobs: JobRepository) -> FastAPI:
    app = FastAPI(title="Slashus Ingestion Service", version="1.0.0")

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health", tags=["health"], include_in_schema=False)
    def legacy_health(response: Response) -> dict[str, str]:
        """Compatibility endpoint for existing Compose/Caddy health checks."""
        if not health.ready:
            response.status_code = 503
            return {"status": "not_ready"}
        return {"status": "healthy"}

    @app.get("/health/ready", tags=["health"])
    def ready(response: Response) -> dict[str, str]:
        if not health.ready:
            response.status_code = 503
            return {"status": "not_ready"}
        return {"status": "ready"}

    @app.get("/jobs/{job_id}", tags=["jobs"])
    def job(job_id: str):
        state = jobs.get(job_id)
        if state is None:
            raise HTTPException(status_code=404, detail="job not found")
        return state.model_dump(mode="json")

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
