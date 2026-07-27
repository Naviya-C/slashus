# Ingestion service image (Kafka worker: doc.uploaded -> ingest -> doc.chunks).
#
# Build from the REPO ROOT (must contain `ingestion-service/`, `shared/contracts/`,
# and `shared/piliwela/`):
#
#   docker build -f ingestion-service/Dockerfile -t ingestion-service .

# ── stage 1: build the piliwela Rust wheel ───────────────────────────────
FROM python:3.12-slim AS piliwela-builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Rust toolchain (needed by maturin to compile piliwela)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip install maturin
COPY services/shared/piliwela /build/piliwela

WORKDIR /build/piliwela
# produce a wheel in /build/piliwela/target/wheels/
RUN maturin build --release --out /wheels

# ── stage 2: runtime ─────────────────────────────────────────────────────
FROM python:3.12-slim 

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ca-certificates: TLS for GCS/Kafka; tesseract (+ Sinhala data) for OCR
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates tesseract-ocr tesseract-ocr-sin \
    && rm -rf /var/lib/apt/lists/*

# install the prebuilt piliwela wheel from stage 1 (no Rust in the final image)
COPY --from=piliwela-builder /wheels /wheels
RUN pip install /wheels/*.whl

# shared contracts
COPY services/shared/contracts /app/shared/contracts
RUN pip install /app/shared/contracts

COPY services/shared/storage /app/shared/storage
RUN pip install /app/shared/storage

#COPY shared/piliwela /app/shared/piliwela
#RUN pip install /app/shared/piliwela

# service deps (piliwela is NOT in requirements.txt — it's the wheel above)
COPY services/ingestion-service/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# service code
COPY services/ingestion-service/src /app/src
RUN touch /app/src/__init__.py /app/src/messaging/__init__.py

RUN useradd --create-home appuser
USER appuser

EXPOSE 8003

# Runs the Kafka consumer (the real workload) on a background thread and a
# thin FastAPI app (GET /health only, for now) on the main thread. See
# src/run_all.py.
CMD ["python", "-m", "src.run_all"]