# syntax=docker/dockerfile:1.9

FROM python:3.12-slim AS deps

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates build-essential \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system --no-cache .

FROM deps AS model
ARG EMBEDDING_MODEL_NAME=BAAI/bge-m3
ENV FASTEMBED_CACHE_PATH=/opt/models

RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='${EMBEDDING_MODEL_NAME}')"

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    FASTEMBED_CACHE_PATH=/opt/models PYTHONPATH=/app/src TOKENIZERS_PARALLELISM=false

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/* && useradd --create-home --uid 10001 appuser

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY --from=model --chown=appuser:appuser /opt/models /opt/models

WORKDIR /app
COPY --chown=appuser:appuser src ./src
USER appuser
EXPOSE 8004 50051

HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8004/health/ready || exit 1

ENTRYPOINT ["python","-m","embedding_service"]
CMD ["serve"]
