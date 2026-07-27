"""FastAPI app (thin).

Previously an empty stub - nothing listened on the port this service exposed
in docker-compose, so `expose: 8003` was dead configuration and the gateway's
GET /jobs/{id} route always 502'd.

This currently provides liveness/readiness only. Real job-status tracking
(GET /jobs/{id} returning per-document ingestion progress) needs a shared
store - e.g. a Redis or Postgres table keyed by job id, written to by this
consumer as it processes each document and read here - which does not exist
yet anywhere in this codebase. Wiring that up means touching the message
contract (job id must be generated at upload time and carried through Kafka),
upload-service, and this service together; it's a real feature to design, not
a one-file fix, so it's intentionally left for a follow-up rather than guessed
at here.
"""

from fastapi import FastAPI

app = FastAPI(title="ingestion-service")


@app.get("/health")
def health() -> dict:
    """Liveness only - does not touch Kafka or storage.

    Mirrors auth-service's own health check design: a readiness probe that
    calls out to a dependency turns a brief outage into a container restart
    loop. Keep this cheap and dependency-free.
    """
    return {"status": "ok"}
