"""
Async gRPC client onto embedding-service.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from enum import StrEnum

import grpc
import structlog
from grpc import aio as grpc_aio

from agentic_service.config.settings import VectorSettings
from agentic_service.domain.models import (
    SearchHit,
    SearchOutcome,
    TitleInfo,
    TitleListing,
)
from agentic_service.observability.metrics import VECTOR_ERRORS
from agentic_service.proto_gen import search_pb2, search_pb2_grpc

log = structlog.get_logger(__name__)

_MODES = {
    "hybrid": search_pb2.SEARCH_MODE_HYBRID,
    "dense": search_pb2.SEARCH_MODE_DENSE,
    "sparse": search_pb2.SEARCH_MODE_SPARSE,
}

OWNERSHIP_KEYS = frozenset({"user_id", "doc_id"})


def as_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [str(v) for v in value if v is not None and str(v) != ""]
    return [str(value)] if str(value) != "" else []


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Fail fast during a sustained outage instead of paying every timeout."""

    def __init__(self, *, failure_threshold: int = 5, recovery_seconds: float = 30.0) -> None:
        self._threshold = failure_threshold
        self._recovery = recovery_seconds
        self._failures = 0
        self._opened_at = 0.0
        self._state = BreakerState.CLOSED

    @property
    def state(self) -> BreakerState:
        if (
            self._state is BreakerState.OPEN
            and time.monotonic() - self._opened_at >= self._recovery
        ):
            self._state = BreakerState.HALF_OPEN
            log.info("breaker.half_open")
        return self._state

    def allows(self) -> bool:
        return self.state is not BreakerState.OPEN

    def record_success(self) -> None:
        if self._state is not BreakerState.CLOSED:
            log.info("breaker.closed")
        self._failures = 0
        self._state = BreakerState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold and self._state is not BreakerState.OPEN:
            self._state = BreakerState.OPEN
            self._opened_at = time.monotonic()
            log.warning("breaker.opened", failures=self._failures)


class GrpcVectorClient:
    def __init__(self, settings: VectorSettings) -> None:
        self._cfg = settings
        options = [
            ("grpc.max_receive_message_length", 16 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 30_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.keepalive_permit_without_calls", 1),
        ]
        if settings.tls_enabled:
            root: bytes | None = None
            if settings.tls_ca_file:
                with open(settings.tls_ca_file, "rb") as f:
                    root = f.read()
            credentials = grpc.ssl_channel_credentials(root_certificates=root)
            self._channel = grpc_aio.secure_channel(settings.grpc_url, credentials, options=options)
        else:
            self._channel = grpc_aio.insecure_channel(settings.grpc_url, options=options)

        self._stub = search_pb2_grpc.VectorSearchStub(self._channel)
        self._breaker = CircuitBreaker()
        log.info("vector.client_ready", target=settings.grpc_url, tls=settings.tls_enabled)

    def _metadata(self, correlation_id: str | None) -> list[tuple[str, str]]:
        metadata = [("x-correlation-id", correlation_id)] if correlation_id else []
        if self._cfg.service_token:
            metadata.append(("x-service-token", self._cfg.service_token.get_secret_value()))
        return metadata

    async def search(
        self,
        *,
        query: str,
        user_id: str,
        doc_ids: Sequence[str] = (),
        limit: int = 10,
        filters: dict[str, list[str]] | None = None,
        mode: str = "hybrid",
        language: str = "si",
        correlation_id: str | None = None,
    ) -> SearchOutcome:
        if not self._breaker.allows():
            VECTOR_ERRORS.labels(code="CIRCUIT_OPEN").inc()
            return SearchOutcome(failed=True, error="search backend unavailable")

        content = {
            key: search_pb2.FilterValues(values=as_values(value))
            for key, value in (filters or {}).items()
            if key not in OWNERSHIP_KEYS and as_values(value)
        }

        try:
            response = await self._stub.Search(
                search_pb2.SearchRequest(
                    query=query,
                    user_id=user_id,
                    doc_ids=list(doc_ids),
                    limit=limit,
                    mode=_MODES.get(mode, search_pb2.SEARCH_MODE_HYBRID),
                    language=language,
                    filters=content,
                ),
                timeout=self._cfg.search_timeout_seconds,
                metadata=self._metadata(correlation_id),
            )
        except grpc.RpcError as exc:
            self._breaker.record_failure()
            code = exc.code().name if exc.code() else "UNKNOWN"
            VECTOR_ERRORS.labels(code=code).inc()
            log.error("vector.search_failed", code=code, detail=exc.details())
            return SearchOutcome(failed=True, error=f"{code}: {exc.details()}")

        self._breaker.record_success()

        requested = {key for key in content if not key.startswith("_")}
        if ignored := requested - set(response.filters_applied):
            log.warning("vector.filters_ignored", keys=sorted(ignored))

        return SearchOutcome(
            hits=[
                SearchHit(
                    chunk_id=h.chunk_id,
                    score=h.score,
                    content=h.content,
                    title=h.title,
                    page=h.page,
                    doc_id=h.doc_id,
                    source=h.source,
                    dense_rank=h.dense_rank,
                    sparse_rank=h.sparse_rank,
                    payload=dict(h.extra),
                )
                for h in response.hits
            ],
            language_used=response.language_used,
            collection_used=response.collection_used,
            user_has_no_documents=response.user_has_no_documents,
            total_user_chunks=response.total_user_chunks,
            filters_applied=list(response.filters_applied),
            degraded=response.degraded,
        )

    async def list_titles(
        self,
        *,
        user_id: str,
        doc_ids: Sequence[str] = (),
        limit: int = 0,
        correlation_id: str | None = None,
    ) -> TitleListing:
        """
        Empty listing on failure rather than raising.

        Title matching is an optimisation: without it retrieval falls back to
        searching the whole corpus, which is worse but works. A dead title scan
        must not take chat down with it.
        """
        if not self._breaker.allows():
            return TitleListing(failed=True)

        try:
            response = await self._stub.ListTitles(
                search_pb2.ListTitlesRequest(user_id=user_id, doc_ids=list(doc_ids), limit=limit),
                timeout=self._cfg.titles_timeout_seconds,
                metadata=self._metadata(correlation_id),
            )
        except grpc.RpcError as exc:
            code = exc.code().name if exc.code() else "UNKNOWN"
            VECTOR_ERRORS.labels(code=code).inc()
            log.warning("vector.list_titles_failed", code=code)
            return TitleListing(failed=True)

        if response.truncated:
            log.warning("vector.titles_truncated", user_id=user_id)

        return TitleListing(
            titles=[TitleInfo(title=t.title, chunk_count=t.chunk_count) for t in response.titles],
            total_chunks=response.total_chunks,
            truncated=response.truncated,
        )

    async def embed(self, texts: list[str], *, purpose: str = "document") -> list[list[float]]:
        """
        Embed text for the long-term memory store.

        Routed through embedding-service so exactly one BGE-M3 exists in the
        deployment a second copy loaded here would double resident memory and
        could drift to a different model version, silently making previously
        written memories unsearchable.
        """
        if not texts:
            return []
        request = search_pb2.EmbedRequest(
            texts=texts,
            purpose=(
                search_pb2.EMBED_PURPOSE_DOCUMENT
                if purpose == "document"
                else search_pb2.EMBED_PURPOSE_QUERY
            ),
        )
        try:
            response = await self._stub.Embed(
                request,
                timeout=self._cfg.search_timeout_seconds,
                metadata=self._metadata(None),
            )
        except grpc.RpcError as exc:
            code = exc.code().name if exc.code() else "UNKNOWN"
            VECTOR_ERRORS.labels(code=code).inc()
            log.error("vector.embed_failed", code=code)
            raise RuntimeError(f"embedding unavailable: {code}") from exc
        return [list(v.values) for v in response.dense]

    async def healthy(self) -> bool:
        """
        Probes the standard gRPC health service.
        """
        from grpc_health.v1 import health_pb2, health_pb2_grpc

        try:
            stub = health_pb2_grpc.HealthStub(self._channel)
            response = await stub.Check(
                health_pb2.HealthCheckRequest(service="slashus.search.v2.VectorSearch"),
                timeout=5,
            )
            return bool(response.status == health_pb2.HealthCheckResponse.SERVING)
        except grpc.RpcError:
            return False

    async def close(self) -> None:
        await self._channel.close()
