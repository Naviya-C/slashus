FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch first, so sentence-transformers doesn't drag in CUDA (~2GB)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# shared contracts
COPY services/shared/contracts /app/shared/contracts
RUN pip install /app/shared/contracts



# service deps
COPY services/embedding-service/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# service code
COPY services/embedding-service/embedding_service /app/embedding_service

# writable dir for the sparse vocab (SPARSE_VOCAB_PATH default lives here).
RUN mkdir -p /app/_store && useradd --create-home appuser && chown -R appuser /app/_store
USER appuser

EXPOSE 8004 50051

# One-time before first run (creates the Qdrant collection):
#   python -m embedding_service.embedding.create_collection
#
# Runs the Kafka consumer on a background thread and a thin FastAPI app
# (GET /health only, for now) on the main thread. See run_all.py.
CMD ["python", "-m", "embedding_service.run_all"]
