# Running and testing locally

## 1. Install

```bash
cd agentic-service
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

First install pulls `sentence-transformers`, which brings CPU torch — a few
minutes and ~2 GB.

## 2. Configure

```bash
cp .env.example .env
```

Fill in:

| Variable | Where from |
|---|---|
| `GROQ_API_KEY` | console.groq.com |
| `GROQ_MODEL` | **verify the exact string** in Groq's model list — `qwen-3.6-27b` is a guess |
| `GEMINI_API_KEY` | you already have this |
| `EMBEDDING_GRPC_URL` | `embedding-service:50051`, or `localhost:50051` running locally |
| `DATABASE_URL` | a **new** Neon database, not auth's or upload's |
| `REDIS_URL` | `redis://localhost:6379/2` if running Redis locally |

No Qdrant credentials here any more, and no `sparse_vocab.json` — embedding-
service owns both and this service reaches them only over gRPC. If the vocab
is missing, it is missing *there*, and `scripts/check.py` reports it via the
vocab hash in the Health response.

Optional retrieval flags, all with working defaults:

| Variable | Default |
|---|---|
| `ENABLE_KEYWORD_EXTRACTION` | `true` |
| `TITLE_STRATEGY` | `bm25` (`none` \| `bm25` \| `llm`) |
| `TITLE_APPLY_AS` | `boost` (`boost` \| `filter`) |

## 3. Migrate

```bash
alembic -c database/alembic.ini upgrade head
```

## 4. Check before starting

```bash
PYTHONPATH=src python scripts/check.py
```

This validates config, prompt templates, agent registration, routes, and live
connectivity to Postgres, Qdrant, Groq and Redis. Every one of these failures
otherwise surfaces as a 500 several layers deep, with a stack trace naming the
symptom rather than the cause.

Expected output when everything is right:

```
--- config ---
  ok   environment — required vars present
  ok   settings — model=qwen3.6-plus, rerank=False, title=bm25/boost

--- code ---
  ok   prompt templates — 6 templates render
  ok   agents registered — generate, mark, retrieve
  ok   FastAPI app — 10 routes

--- services ---
  ok   postgres — 5 tables present
  ok   embedding-service — ok (vocab 4f2a9c1b8e07)
  ok   ListTitles — 23 titles, 1432 chunks
  ok   qwen — responded ('OK')
  ok   redis — reachable

all checks passed (0 warnings).
```

Set `CHECK_USER_ID` to a real user id to exercise `ListTitles`; without it
that check is skipped with a warning. Exit code is 1 if anything failed, so
this can gate a deploy.

Note it probes embedding-service's **gRPC** port, not its HTTP `/health`.
The HTTP probe can pass while the gRPC thread is dead, and that combination
is exactly what makes chat hang with nothing in the logs.

## 5. Start

```bash
PYTHONPATH=src uvicorn api.server:api --port 8084 --reload
```

First request loads BGE-M3 (~2 GB, one-off). Expect 30–60 s before the first
response; subsequent ones are fast.

## 6. Test frontend

In a second terminal:

```bash
streamlit run frontend/app.py
```

Set **X-User-Id** in the sidebar to a user whose documents are already in
Qdrant — take it from a payload:

```json
{"user_id": "ab6ed345-ccc6-40d1-9b84-dde98ea43aff", "doc_id": "20ff7caf-..."}
```

Any other id and preflight will correctly refuse every request, which looks
like a bug and isn't.

This UI bypasses api-gateway and sets `X-User-Id` itself. In production the
gateway sets it from a verified token and the client cannot influence it —
which is why this file must never ship.

---

## What to test, in order

Each step isolates one layer, so a failure tells you where to look.

**1. Preflight** — set a random uuid as the user id, ask anything.
Expect: "You haven't uploaded any documents yet."
Proves: Qdrant filtering and the `no_documents` path.

**2. Intent + answer** — real user id, ask a factual question about the
material.
Expect: a written answer in the conversation, `kind: message`.
Proves: routing, retrieval, `ANSWER.md`, grounding.

**3. Irrelevant question** — ask about something the documents don't cover.
Expect: "I found related material, but it doesn't cover this."
Proves: `not_in_source`, i.e. the model refusing rather than inventing. This
is the most important single behaviour to verify.

**4. MCQ generation** — "give me 5 mcq questions about X".
Expect: five questions in the right panel with radio buttons.
Proves: artifact detection, `GENERATE_MCQ.md`, normalization, persistence.

**5. Instant MCQ marking** — answer them, press Mark.
Expect: marks with no perceptible delay.
Proves: MCQ marking never calls an LLM.

**6. Essay generation and marking** — "give me an essay question about X",
answer it badly on purpose.
Expect: a mark under 5 with the model answer revealed.
Proves: `GENERATE_WRITTEN.md`, rubric generation, `MARK_WRITTEN.md`, the
reveal rule.

**7. Continuation** — "give me more".
Expect: five different questions.
Proves: Redis scratch and the previous-question exclusion.

**8. Sessions** — reload the page, click a session in the sidebar.
Expect: the conversation restores.
Proves: keyset pagination and repository scoping.

**9. Document filter** — paste one `doc_id`, ask about something only in
another document.
Expect: `not_in_source`.
Proves: `doc_id` filtering with `MatchAny`.

**10. Filter recovery** — set `TITLE_APPLY_AS=filter`, then ask about a lesson
using slightly different wording from its stored title.
Expect: an answer, plus `zero hits under content filters ['lesson_title'] —
dropping them and retrying` in the log.
Proves: the recovery path. Before it, this exact case returned "your documents
don't cover this" while the lesson sat in the index. Worth running at least
once, because it is the failure mode that produces no error anywhere.

---

## Where things break first

**Malformed JSON from Qwen.** `src/agents/generator/normalize.py` is where it
surfaces — put the first breakpoint there. Symptom: `generation_empty` in the
response errors, or questions silently dropped. The `logger.warning` lines in
that file name the exact reason.

**Wrong model string.** Groq returns a 404 that reads like an auth failure.
`scripts/check.py` catches this before you start.

**Empty retrieval on a user who does have documents.** Usually the payload
field names — this code filters on `user_id` and `doc_id`, matching your
payload. If yours differs, `agents/retrieval/agent.py` is where to change it.

**Sparse leg silently dead.** Look at `dense/sparse=` in the retrieve log
line. `12/0` means the sparse leg returned nothing, which is almost always a
missing or stale `sparse_vocab.json` in embedding-service rather than a hard
query. Hybrid degrades to dense-only with no error on either side; results
merely get slightly worse.

**Sinhala intent misrouting.** Log every routing decision and look at the
`method` field: `embedding` means the classifier was confident, `llm` means it
fell through, `default` means neither worked. A lot of `default` means the
examples in `orchestrator/router/classifier.py` need your real phrasings.

---

## Adding to docker-compose

```yaml
  agentic-service:
    build:
      context: ./services/agentic-service
    container_name: agentic
    env_file:
      - ./services/agentic-service/.env
    environment:
      REDIS_URL: redis://redis:6379/2
    depends_on:
      redis:
        condition: service_healthy
    expose:
      - "8084"
    volumes:
      # BGE-M3 cache — without this it re-downloads ~2GB on every rebuild.
      - ./data/huggingface:/home/appuser/.cache/huggingface
      - ./data/sparse_vocab/sparse_vocab.json:/app/_store/sparse_vocab.json:ro
    restart: unless-stopped
```

The gateway already points `AGENTIC_URL` at `http://agentic:8084`, so the
`/chat`, `/mark` and `/sessions` routes start working once this is up.

Chown the mounts before first start, or the container's non-root user cannot
write the model cache:

```bash
sudo chown -R 1000:1000 ./data/huggingface
```
