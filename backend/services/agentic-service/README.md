# agentic-service v4

Slashus is a model-controlled ReAct tutoring agent. `langchain.agents.create_agent`
binds native tools to the model; Python enforces tenancy, limits, persistence,
grounding metadata, and side effects without prescribing a fixed route.

The model may answer directly, list indexed lessons, perform one or more hybrid
searches, reformulate a Sinhala/English/Singlish query, write memory, generate a
quiz, or evaluate a saved answer. Tool count, recursion depth, and wall-clock
duration remain bounded.

## Memory

| Type | Storage | Behavior |
|---|---|---|
| Working | Redis LangGraph checkpointer | Thread history, summarized before the context limit |
| Semantic | PostgreSQL + pgvector | Student goals, preferences, facts, misconceptions |
| Episodic | PostgreSQL + pgvector | Completed tutoring situations with outcomes |
| Procedural | PostgreSQL + pgvector | Versioned active tutoring rules injected into future prompts |

Recall runs exactly once per new user turn, including later turns in the same
thread. Semantic cache keys include user, document scope, document generation,
and memory generation. Any conversation with prior history is answered live.

## API

- `POST /api/v1/chat` — normal JSON or SSE (`stream: true`)
- `POST /api/v1/mark` — deterministic objective marking or rubric-based written marking
- `GET /api/v1/practice/{set_id}`
- `GET /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `GET /api/v1/memory`
- `DELETE /api/v1/memory/{semantic|episodic|procedural}`

SSE emits `turn_started`, `tool_started`, `tool_completed`, `token`,
`turn_completed`, and structured `error` events. Both chat modes persist the
same logical result and schedule background consolidation.

## Fresh local setup

Python 3.12 and Docker Compose v2 are required. Start infrastructure using the
compose file included in this service; its PostgreSQL image contains pgvector.

```bash
docker compose -f docker-compose.infra.yml up -d

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Set at least:

```dotenv
DATABASE_URL=postgresql+asyncpg://slashus:slashus@localhost:5432/slashus
REDIS_URL=redis://localhost:6379/0
LLM_API_KEY=...
EMBEDDING_GRPC_URL=localhost:50051
EMBEDDING_SERVICE_TOKEN=the-same-value-as-GRPC_SERVICE_TOKEN
SECURITY_GATEWAY_SHARED_SECRET=local-gateway-secret
```

Run migrations after PostgreSQL is healthy:

```bash
alembic upgrade head
python -m agentic_service check
```

Start embedding-service first, then:

```bash
python -m agentic_service serve
```

## Verification

```bash
curl http://localhost:8084/health/ready

curl -X POST http://localhost:8084/api/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: 11111111-1111-1111-1111-111111111111' \
  -H 'X-Gateway-Secret: local-gateway-secret' \
  -d '{"message":"Explain the water cycle","doc_ids":[]}'

curl -N -X POST http://localhost:8084/api/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: 11111111-1111-1111-1111-111111111111' \
  -H 'X-Gateway-Secret: local-gateway-secret' \
  -d '{"message":"Create two MCQs","stream":true}'

curl -X POST http://localhost:8084/api/v1/mark \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: 11111111-1111-1111-1111-111111111111' \
  -H 'X-Gateway-Secret: local-gateway-secret' \
  -d '{"question_id":"REPLACE_WITH_QUESTION_UUID","selected_index":1}'

pytest
```

Stable citations use `[C-XXXXXXXXXX]`. The API returns structured citation
metadata only for identifiers that correspond to chunks retrieved in that turn.
