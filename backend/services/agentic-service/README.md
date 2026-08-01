# Agentic Service

Retrieval, question generation and marking for Slashus.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/chat` | question, generation, or conversation |
| POST | `/mark` | grade a submission |
| GET | `/sessions` | sidebar list (keyset paginated) |
| GET | `/sessions/{id}` | one session's messages (keyset paginated) |
| GET | `/practice/{id}` | restore a practice set with its answers |
| GET | `/health` | liveness |

Identity comes from `X-User-Id`, injected by api-gateway from a verified
token. Every query is user-scoped regardless — Qdrant and Postgres have no
ownership concept of their own.

## Response shape

Every `/chat` response carries `kind`, telling the client where to render:

- `message` → middle column, the conversation
- `questions` → right panel, the practice set
- `marking` → right panel, updates in place

`reply` is always present and always renders in the chat column, so a
generation produces both a chat line and panel content.

When a request cannot be served, `reason` is set — `no_documents`,
`no_relevant`, or `not_in_source`. The frontend switches on that rather than
string-matching the reply.

## Models

Groq / Qwen 3.6 serves intent classification, generation and marking. Qwen was
pre-trained across 119 languages including Sinhala; Llama 3.x officially
covers 8, none of them.

Gemini still serves query understanding and the evaluator. Kept separate so a
rate limit on one cannot starve the other.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in
alembic -c database/alembic.ini upgrade head
PYTHONPATH=src uvicorn api.server:api --port 8084
```

## Tests

```bash
python -m pytest tests/ -q
```

Contract tests only — pure functions where a silent bug is most expensive.
Anything needing a live Qdrant, Postgres or Groq belongs in an integration
suite that does not exist yet.

## Retrieval pipeline

```
query
  ├─ dense  (BGE-M3)          ─┐
  └─ sparse (Qdrant TF/IDF)   ─┴─ RRF fusion (0.7 / 0.3)
                                     │
                                     ├─ BM25 fusion      free, local, always on
                                     ├─ LLM rerank       off by default
                                     └─ diversify        near-duplicate removal
```

**BM25** (`core/retrieval/bm25.py`) is computed over the retrieved candidate
pool with real k1 saturation and b length normalization — neither of which the
Qdrant sparse leg provides, since both are functions of document statistics
written at ingest.

Because IDF comes from the candidate pool rather than the corpus, this is a
RE-RANKING signal: it reorders what dense and sparse found, and cannot surface
something both missed. Corpus-wide BM25 needs ingestion to write BM25-weighted
document vectors; the exact formula is at the bottom of that file.

**Diversify** uses token-set Jaccard, not content hashing. Sliding-window
chunks share ~80% of their text but hash differently, so the previous exact-
match dedup let both through and the LLM received the same passage twice.

## Cost controls

`ENABLE_RERANKING=false` by default. The retrieval loop reranks on every
attempt and runs up to `max_retries + 1` times, so one question could burn 4
LLM calls before producing anything. When on, only the top
`settings.rerank_top_k` (30) hits are reranked — at `max_chunk_budget` the
overfetch reaches 600, which is a 600KB prompt.

MCQ marking never calls an LLM. It is an integer comparison against the
stored `correct_index`.

## Known gaps

- No integration tests. Nothing here has been run against a live Qdrant,
  Postgres or Groq.
- The retrieval consumer has no retry cap: a message that can never succeed
  is redelivered indefinitely. Needs a dead-letter path.
- `summary` and `flashcards` artifacts route through `ANSWER.md` rather than
  dedicated templates.
- `correct_index` ships to the browser for instant MCQ feedback. Acceptable
  for self-directed study; not for graded assessment.
