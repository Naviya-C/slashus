FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10
WORKDIR /build

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install "hatchling>=1.26" \
    && pip wheel --no-build-isolation --prefer-binary --wheel-dir /wheels ".[vision]"

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       libmagic1 \
       tesseract-ocr \
       tesseract-ocr-eng \
       tesseract-ocr-sin \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install /wheels/* && rm -rf /wheels

USER appuser
EXPOSE 8003

CMD ["ingestion-service", "serve"]
