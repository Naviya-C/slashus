# syntax=docker/dockerfile:1.9
FROM python:3.12-slim AS deps
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system --no-cache .

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/* && useradd --create-home --uid 10001 appuser
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
WORKDIR /app
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser migrations ./migrations
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
USER appuser
EXPOSE 8084
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8084/health/ready || exit 1
ENTRYPOINT ["python","-m","agentic_service"]
CMD ["serve"]
