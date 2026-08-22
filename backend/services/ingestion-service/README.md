# Slashus ingestion service

Production-oriented, asynchronous document ingestion for the Slashus retrieval platform.
The service consumes object-storage references from Kafka, streams documents unit-by-unit,
publishes embedding-ready chunks immediately, records durable job progress in Redis, and
optionally queues images for a separately deployable vision worker.

## What changed

- Removed the repository-local Rust/Python `shared/piliwela` build. The service installs
  [`piliwela`](https://pypi.org/project/piliwela/) from PyPI and keeps a thin adapter around
  `convert_auto_with_metadata(text, font_name)`.
- Replaced whole-document buffering with page/slide/sheet streaming.
- Replaced synchronous Gemini calls in the ingestion path with optional image-enrichment events.
- Downloads source objects directly to a temporary file instead of holding the full file in RAM.
- Added durable attempt counts, job progress, bounded retries, DLQs, metrics, structured logs,
  deterministic chunk IDs, compressed Kafka publication, and graceful worker shutdown.
- Removed the second PDF parser. PyMuPDF now handles text, layout, tables, images, and rendering;
  table boxes are excluded from normal text to avoid duplicate content.
- Restored the original textbook lesson-title strategy: one reliable large title, positional
  assignment, split-title merging, and title carry-over across subsequent pages.

## Supported formats

| Format | Extraction strategy |
|---|---|
| PDF | Layout text, headings, tables, images; page OCR when digital text is insufficient |
| DOCX | Paragraph styles, headings, lists, tables, embedded images |
| PPTX | Slide titles, text frames, tables, embedded pictures |
| XLSX | Read-only, sheet-by-sheet tabular extraction |
| PNG/JPEG/WebP/TIFF/BMP | Local OCR plus optional background vision enrichment |
| TXT/Markdown/RST/XML/YAML/log | UTF-8 text extraction with replacement for damaged bytes |
| HTML | Scripts/styles removed, visible text retained |
| CSV/TSV | Row-preserving table extraction |
| JSON/JSONL | Validated and normalized structured text |

No production system safely supports literally every file type. Unknown formats are rejected and
sent to the upload DLQ. Legacy binary Office files (`.doc`, `.ppt`, `.xls`) should be converted in
a sandboxed LibreOffice conversion worker before publishing `documents.uploaded`; keeping that
large native converter outside this service reduces its attack surface and image size.

## Runtime architecture

```text
documents.uploaded
        |
        v
ingestion worker ----> Redis job status
        |
        +---- page chunks ----> documents.chunks ----> embedding service
        |
        +---- image refs -----> documents.images ----> optional vision worker
        |
        +---- completion -----> documents.ingested
```

The normal ingestion worker never calls Gemini. An image receives local OCR or a deterministic
description immediately, so the document can become searchable even when the vision provider is
unavailable. The optional vision worker later publishes an improved chunk with the same
deterministic `chunk_id`; the embedding service and Qdrant overwrite the existing point.

## Image rate-limit strategy

The vision worker provides four controls across all replicas:

1. A Redis-backed global requests-per-minute limit.
2. A Redis circuit breaker opened immediately after a `429`.
3. SHA-256 caption caching for duplicate images.
4. Kafka retry without acknowledging rate-limited events.

Start conservatively:

```dotenv
VISION_ENRICHMENT_ENABLED=false
VISION_REQUESTS_PER_MINUTE=10
VISION_MAX_ATTEMPTS=3
VISION_CIRCUIT_SECONDS=90
```

Enable enrichment only after creating the `documents.images` topic and deploying the vision worker.
Do not increase the number of vision replicas without keeping Redis-based global limiting enabled;
per-process limits multiply when replicas scale.

For high volume, prefer a paid provider quota or a self-hosted caption model on a GPU worker.
Provider calls remain an optional quality improvement, never a document-readiness dependency.

## Event compatibility

`documents.uploaded` accepts the existing schema and an additive optional `job_id`:

```json
{
  "schema_version": 1,
  "doc_id": "uuid",
  "user_id": "uuid",
  "source_name": "grade-10-science.pdf",
  "storage_key": "user-id/doc-id/source.pdf",
  "content_type": "application/pdf",
  "job_id": "uuid"
}
```

`documents.chunks` preserves the fields consumed by the current embedding service. It adds
`block_type` beside the older `type` field for compatibility. Unknown additive fields are safe
because the embedding service uses Pydantic with `extra="allow"`.

## Local setup

Python 3.12 is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,vision]"
cp .env.example .env
```

For local object storage:

```dotenv
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=/tmp/slashus-storage
```

Source keys resolve beneath `/tmp/slashus-storage/source`; extracted assets are written beneath
`/tmp/slashus-storage/assets`.

Run the normal worker and health API:

```bash
ingestion-service serve
```

Run the optional vision worker as a separate deployment/process:

```bash
ingestion-service vision-worker
```

Endpoints:

```text
GET /health/live
GET /health/ready
GET /jobs/{job_id}
GET /metrics
```

## Docker

Build from this directory:

```bash
docker build -t slashus-ingestion:1.0.0 .
```

The Dockerfile installs the published Piliwela wheel directly. Rust, Maturin, and the old
`shared/piliwela` directory are no longer required.

Run the image with `serve` for normal ingestion. Override the command for vision:

```bash
docker run --env-file .env slashus-ingestion:1.0.0 ingestion-service vision-worker
```

## Kafka topics

Create these topics before rollout:

```text
documents.uploaded
documents.chunks
documents.images
documents.ingested
documents.uploaded.dlq
documents.images.dlq
```

Recommended production properties:

```text
replication.factor=3
min.insync.replicas=2
compression.type=producer
```

Start `documents.chunks` with enough partitions for the future embedding worker count. Chunk events
use `doc_id:unit_number` as the key, allowing separate pages/slides/sheets of one document to be
processed by different embedding replicas.

Only durable object-storage references belong in upload events; PDFs and large page payloads never
travel through Kafka. The worker publishes bounded chunk events as extraction progresses.

### Google Managed Service for Apache Kafka

Set `KAFKA_USE_GCP_ADC=true` to use SASL/OAUTHBEARER with Application Default Credentials. The
included GKE manifest uses Workload Identity Federation, so no service-account key is stored in a
Secret. Grant its Kubernetes service-account principal `roles/managedkafka.client`, replace the
bootstrap placeholder, and keep the cluster on a supported GKE release. For local development,
leave this disabled and use the normal protocol/SASL settings.

## Reliability semantics

- Upload offsets commit only after all chunk events and the completion event are acknowledged.
- The Redis attempt count survives process and OOM restarts.
- After the configured maximum attempts, the upload event moves to the DLQ and the partition advances.
- Chunk IDs are deterministic UUID5 values, so reprocessing overwrites Qdrant points safely.
- Malformed upload and vision events go to separate DLQs.
- A completed Redis job causes a redelivered upload event to be committed without reprocessing.

## Tests and checks

```bash
python -m compileall -q src tests
pytest
ruff check src tests
mypy src
```

Tests cover wire compatibility, chunk boundaries, multilingual text, and common Office readers.
Integration tests against Kafka, Redis, GCS, Tesseract, and the embedding consumer should run in
staging because those checks require real service dependencies and credentials.

## Deployment order

1. Publish the new container without enabling vision enrichment.
2. Create Kafka topics and verify the upload and chunk contracts in staging.
3. Deploy one ingestion replica and process PDF, scanned PDF, DOCX, image, PPTX, XLSX, and text fixtures.
4. Verify `time_to_first_chunk`, chunk count, DLQ count, memory, and consumer lag.
5. Scale ingestion replicas from upload-topic lag.
6. Deploy the separate vision worker with a low global RPM limit.
7. Increase the vision limit only after checking the provider project quota and real `429` metrics.

## Important operational metrics

```text
ingestion_document_seconds
ingestion_documents_completed_total
ingestion_documents_failed_total
ingestion_units_processed_total
ingestion_chunks_published_total
ingestion_images_queued_total
ingestion_consumer_lag_messages
ingestion_dlq_documents_total
ingestion_vision_requests_total
ingestion_vision_circuit_open
```
