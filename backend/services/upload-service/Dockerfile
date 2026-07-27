# Upload service image.
#
# IMPORTANT: build from the REPO ROOT (the dir containing both `upload-service/`
# and `shared/contracts/`), so the shared contracts package is in the context:
#
#   docker build -f upload-service/Dockerfile -t upload-service .
#
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN mkdir -p /data/uploads

# TLS roots for GCS/Kafka. (confluent-kafka ships manylinux wheels that bundle
# librdkafka, so no compiler/apt build deps are needed.) 
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 1) shared contracts first — its own layer, rarely changes, caches well
COPY services/shared/contracts /app/shared/contracts
RUN pip install /app/shared/contracts

COPY services/shared/storage /app/shared/storage
RUN pip install /app/shared/storage

# 2) service deps
COPY services/upload-service/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# 3) service code
COPY services/upload-service/upload_service /app/upload_service

# run unprivileged
RUN useradd --create-home appuser
USER appuser

EXPOSE 8002

# host 0.0.0.0 so the container is reachable; single worker keeps the Kafka
# producer and GCS client as one instance (scale by running more containers).
CMD ["uvicorn", "upload_service.app:app", "--host", "0.0.0.0", "--port", "8002"]
