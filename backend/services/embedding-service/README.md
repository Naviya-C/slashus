# embedding-service v4

This service owns document ingestion, BGE-M3 dense embeddings, Sinhala-aware
stateless sparse encoding, Qdrant storage, and gRPC retrieval.

BGE-M3 uses its official 1024-dimensional ONNX export. The service registers
that export through FastEmbed's stable custom-model API at both image build
time and process startup. No E5 query or passage prefixes are applied.

Sparse indices are deterministic hashes of Sinhala/English/numeric tokens. No
local vocabulary, corpus-level BM25 index, or local IDF database exists. Qdrant
applies `Modifier.IDF`; Qdrant also performs dense+sparse RRF inside each search
branch.

When the agent supplies high-confidence indexed lesson choices, retrieval runs:

- title-constrained hybrid branch, weight `0.80`
- global hybrid branch, weight `0.20`

The branches are combined with weighted reciprocal-rank fusion, deduplicated by
chunk ID, then diversified. Below the confidence threshold, lesson constraints
are dropped and retrieval remains global.

Kafka delivery is at-least-once. UUID5 point IDs make redelivery idempotent.
Failed batches seek every affected partition back to its first failed offset;
offsets are committed only after Qdrant succeeds or confirmed DLQ delivery.

## Fresh local setup

Start PostgreSQL, Redis, Kafka, and Qdrant from the agentic-service compose file.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Set at least:

```dotenv
QDRANT_ENDPOINT=http://localhost:6333
QDRANT_COLLECTION=sinhala_books_v5
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_DIMENSIONS=1024
EMBEDDING_QUERY_PREFIX=
EMBEDDING_DOCUMENT_PREFIX=
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_URL=redis://localhost:6379/0
GRPC_SERVICE_TOKEN=the-same-value-as-EMBEDDING_SERVICE_TOKEN
```

Create or validate the collection and all payload indexes. The command is
idempotent and refuses incompatible dense dimensions or missing named vectors.

```bash
python -m embedding_service create-collection
python -m embedding_service check
python -m embedding_service serve
```

Verify:

```bash
curl http://localhost:8004/health/ready
python -m grpc_tools.protoc -I proto --python_out=/tmp --grpc_python_out=/tmp proto/search.proto
pytest
```

## Test ingestion event

Publish a validated chunk to `documents.chunks`:

```bash
docker compose -f ../agentic-service/docker-compose.infra.yml exec -T kafka \
  kafka-console-producer.sh --bootstrap-server kafka:9092 --topic documents.chunks <<'JSON'
{"chunk":{"chunk_id":"demo-1","doc_id":"22222222-2222-2222-2222-222222222222","user_id":"11111111-1111-1111-1111-111111111111","text":"ජල චක්‍රයේ වාෂ්පීකරණය ඝනීභවනය සහ වර්ෂාපතනය යන අදියර ඇතුළත් වේ.","embed_text":"ජල චක්‍රයේ වාෂ්පීකරණය ඝනීභවනය සහ වර්ෂාපතනය යන අදියර ඇතුළත් වේ.","source_name":"science.pdf","page":3,"section_path":["ජල චක්‍රය"]}}
JSON
```

Successful ingestion increments the user's Redis document generation, so old
semantic-cache answers cannot survive a document update.
