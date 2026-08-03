# Architecture

```
                    Caddy :443  (only published port)
                         │
                    api-gateway :8080
                         │
      ┌──────────────┬───┴────────┬──────────────┐
      │              │            │              │
 auth-service   upload-service  ingestion   agentic-service
   :8081           :8002         :8003          :8084
      │              │            │              │
    Neon            GCS         Kafka        gRPC :50051
                     │            │              │
                     └──── Kafka ─┘              ▼
                                          embedding-service
                                            :8004 / :50051
                                                 │
                                          Qdrant + BGE-M3
```

## What changed in this pass

**agentic-service no longer touches Qdrant.** It used to open its own
QdrantClient, load its own BGE-M3 (~2.2 GB), and read its own copy of
`sparse_vocab.json`. Now embedding-service owns all three and serves search
over gRPC.

That removed:

| | Before | After |
|---|---|---|
| BGE-M3 instances | 2 | 1 |
| Views of the sparse vocab | 2 (one going stale) | 1 |
| Services that can query Qdrant | 2 | 1 |
| agentic image size | GBs (torch) | ~300 MB |
| agentic mem_limit | ~3 GB | 768 MB |

**Ownership filter moved server-side.** embedding-service owns Qdrant, so it
enforces access to Qdrant. A caller passing `user_id` and hoping it is honoured
is how one bug returns another user's chunks.

**Search only, not the retrieval loop.** Retries, query rewriting, budget
escalation, BM25 fusion and diversification stay in agentic-service — they are
retrieval *policy* and change as prompts are tuned. Putting them behind gRPC
would mean redeploying the ingestion consumer to tune retrieval.

## Why gRPC and not Kafka

Kafka is for fire-and-forget async — the ingest pipeline is exactly that.
Search is synchronous request/response with a user watching a spinner. Doing
that over a broker means inventing correlation ids, a reply topic, a timeout,
and a pending-request map: RPC, badly.

Protobuf also matters for the payload here. JSON escapes every Sinhala
character to `\uXXXX`, so a 1200-character chunk becomes ~7200 bytes.
Protobuf sends UTF-8 directly — roughly 6× smaller on the field that dominates
the response.

## The asymmetric embedding contract

BGE-M3 embeds a query differently from a document — `LocalEmbedder.embed()`
prefixes `"query: "`, `embed_documents()` does not. Mixing them degrades
retrieval with no error anywhere. `EmbedPurpose` is an explicit enum on the
proto so a caller cannot forget which side it is on.

## The sparse vocab

`sparse_vocab.json` maps term → index, and ingest APPENDS to it. Append-only
matters: existing tokens keep their indices, so previously-indexed points stay
valid — which is why the vocab can grow without re-encoding.

Two things were wrong and are now fixed:

- `save()` truncated the file before writing. A crash mid-write left unparseable
  JSON, the encoder silently restarted from empty, and every sparse query
  matched nothing. Now writes to a temp file and renames — atomic on POSIX.
- Two services held it. The reader's copy went stale the moment ingest appended
  a term. One owner now, so the consumer and the search server share one
  in-memory instance.

## Memory budget (8 GB VM)

Every service has an explicit `mem_limit`. Without one, Docker lets any
container take everything and the OOM killer picks by memory-use score — which
is BGE-M3, not whatever caused the spike. A large PDF ingest could kill Caddy
and take the site down.

Total is ~7.2 GB of 8, leaving ~1 GB for the host.

`embedding-service` is also capped at `cpus: "1.0"` — ingest embedding would
otherwise saturate both cores and a search arriving mid-batch waits seconds
behind it. Ingestion getting slower is invisible; search getting slower is not.

## Known gaps

- No integration tests. The gRPC round trip is verified against fakes, not a
  live Qdrant.
- embedding-service is now a hard dependency for chat. Its crash used to only
  lag ingestion.
- Single-writer sparse encoder means it can never scale past one replica, so
  there are no zero-downtime deploys on the search path.
- `GET /jobs/{id}` still 502s — job-status tracking was never built.
- No backups on `./data/`. Kafka logs, Caddy certs and uploads all live there.
