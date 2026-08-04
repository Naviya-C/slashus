# Embedding Service

Owns Qdrant, BGE-M3 and the sparse vocab. Ingests chunks from Kafka and serves
search over gRPC. Nothing else in the system talks to Qdrant.

## Surface

| Transport | Endpoint | Purpose |
|---|---|---|
| HTTP `:8004` | `GET /health` | liveness, for Docker |
| gRPC `:50051` | `Search` | hybrid search, ownership enforced here |
| gRPC `:50051` | `ListTitles` | the exact stored lesson titles for a user |
| gRPC `:50051` | `Embed` | dense + sparse vectors for arbitrary text |
| gRPC `:50051` | `Health` | readiness + sparse vocab hash |

The HTTP surface is one liveness route and deliberately does not touch Qdrant
or Kafka: a readiness probe that calls a dependency turns a brief outage into
a container restart loop.

Run **exactly one instance**. The sparse encoder writes a shared vocab file
and is single-writer.

## What this service does and does not decide

It applies filters and returns ranked hits. It does not run the retrieval
*loop* — no retries, no query rewriting, no budget escalation, no BM25 fusion,
no diversification. Those are policy and live in agentic-service's retrieval
agent, so tuning retrieval never means redeploying the service that also runs
the ingestion consumer.

Two things it does decide, because they need the store and nothing else does:

**Ownership.** `user_id` and `doc_ids` are typed request fields, and the
filter is built here rather than trusted from the caller. Qdrant has no
concept of ownership — a query without `user_id` returns every user's chunks —
so a `Search` without one is rejected outright.

**Which keys are filterable.** `_FILTERABLE` in `grpc_server.py` is an
allowlist. A key that is not in the payload is not an error in Qdrant: it
matches zero points and comes back as a successful empty result, which reads
as "no relevant documents" while the material sits right there. `lesson_no` is
the live example — ingest parses the number out of the section heading and
stores only `lesson_title`, so filtering on it wiped out every hit.

Filter values are strings on the wire, one type for every key, so integer keys
are coerced on arrival. `MatchValue("42")` does not match the integer `42`; it
matches nothing, silently.

## ListTitles

Returns the distinct `lesson_title` values for a user, with chunk counts — the
EXACT stored strings, including any double spaces PDF extraction left behind.

It exists because the caller used to ask an LLM to produce a title and filter
on the result. The model has never seen the corpus, so it produced something
plausible rather than something real, and the filter excluded an entire lesson
while reporting success. Handing back the real strings turns an open-ended
guess into a closed-set choice.

The scan uses payload projection (`with_payload=["lesson_title"]`) and is
capped at 20 pages of 1000. `truncated` says the cap was hit, which matters
before concluding a title does not exist.

## The proto

`proto/search.proto` is duplicated byte-for-byte in agentic-service. Copying
rather than sharing a package is deliberate at seven services: a shared proto
means a version bump has to land in both repos before either can deploy.

**Additive only.** Never renumber a field, never reuse a number. Both services
deploy independently, so at any moment an old client is talking to a new
server or the reverse.

```bash
./scripts/gen_proto.sh          # then do the same in agentic-service
```

The checked-in `search_pb2.py` omits protoc's `ValidateProtobufRuntimeVersion`
call, which pins a *minimum* protobuf runtime and raises on import when the
installed one is older. That turns a version skew between the two services
into an ImportError at startup. The descriptor itself is identical.

## Config

| Variable | Default |
|---|---|
| `QDRANT_CLUSTER_ENDPOINT` | — |
| `QDRANT_CLUSTER_API` | — |
| `QDRANT_COLLECTION` | `sinhala_books_v3` |
| `SPARSE_VOCAB_PATH` | `./_store/sparse_vocab.json` |
| `GRPC_PORT` | `50051` |
| `HTTP_PORT` | `8004` |

Without the vocab file the sparse leg returns nothing and hybrid degrades to
dense-only — silently. `Health` returns a hash of it (`unavailable` when
missing), which is how agentic-service's `scripts/check.py` catches it.

## Crash guards

Every background thread exits the *process* on an unhandled exception rather
than dying quietly. Without that, a dead thread sits behind a healthy HTTP
probe: the container reports fine and nothing works. It matters more now that
search runs here — a dead gRPC thread means chat hangs while `/health` keeps
saying ok.
