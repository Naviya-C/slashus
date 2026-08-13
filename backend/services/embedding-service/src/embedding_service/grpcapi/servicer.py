"""gRPC servicer. Async, with explicit status-code mapping."""

from __future__ import annotations

import hmac

import structlog
from grpc import StatusCode
from grpc.aio import ServicerContext

from embedding_service.config.settings import Settings
from embedding_service.domain.models import SearchMode
from embedding_service.proto_gen import search_pb2, search_pb2_grpc
from embedding_service.store.search import SearchService

log = structlog.get_logger(__name__)

_MODES = {
    search_pb2.SEARCH_MODE_UNSPECIFIED: SearchMode.HYBRID,
    search_pb2.SEARCH_MODE_HYBRID: SearchMode.HYBRID,
    search_pb2.SEARCH_MODE_DENSE: SearchMode.DENSE,
    search_pb2.SEARCH_MODE_SPARSE: SearchMode.SPARSE,
}
MAX_EMBED_TEXTS = 128


class VectorSearchServicer(search_pb2_grpc.VectorSearchServicer):
    def __init__(self, *, settings: Settings, search: SearchService, dense, sparse) -> None:
        self._settings = settings
        self._search = search
        self._dense = dense
        self._sparse = sparse

    async def _authorize(self, context: ServicerContext) -> None:
        expected = self._settings.server.service_token
        if expected is None:
            return
        metadata = {item.key: item.value for item in context.invocation_metadata()}
        if not hmac.compare_digest(
            metadata.get("x-service-token", ""), expected.get_secret_value()
        ):
            await context.abort(StatusCode.UNAUTHENTICATED, "invalid service credential")

    async def Search(self, request, context: ServicerContext):  # noqa: N802
        await self._authorize(context)
        if not request.user_id:
            await context.abort(StatusCode.INVALID_ARGUMENT, "user_id is required")
        if not request.query.strip():
            await context.abort(StatusCode.INVALID_ARGUMENT, "query must not be empty")

        try:
            result = await self._search.search(
                query=request.query,
                user_id=request.user_id,
                doc_ids=list(request.doc_ids),
                limit=request.limit or 10,
                filters={k: list(v.values) for k, v in request.filters.items()},
                mode=_MODES.get(request.mode, SearchMode.HYBRID),
                language=request.language or "si",
            )
        except Exception as exc:
            log.error("grpc.search_failed", user_id=request.user_id, exc_info=True)
            await context.abort(StatusCode.INTERNAL, f"search failed: {type(exc).__name__}")
            raise

        return search_pb2.SearchResponse(
            hits=[
                search_pb2.Hit(
                    chunk_id=h.chunk_id,
                    score=h.score,
                    content=h.content,
                    title=h.title,
                    page=h.page,
                    doc_id=h.doc_id,
                    source=h.source,
                    extra=h.extra,
                    dense_rank=h.dense_rank,
                    sparse_rank=h.sparse_rank,
                )
                for h in result.hits
            ],
            collection_used=result.collection_used,
            language_used=result.language_used,
            user_has_no_documents=result.user_has_no_documents,
            total_user_chunks=result.total_user_chunks,
            filters_applied=result.filters_applied,
            degraded=result.degraded,
        )

    async def ListTitles(self, request, context: ServicerContext):  # noqa: N802
        await self._authorize(context)
        if not request.user_id:
            await context.abort(StatusCode.INVALID_ARGUMENT, "user_id is required")
        try:
            listing = await self._search.list_titles(
                user_id=request.user_id, doc_ids=list(request.doc_ids), limit=request.limit
            )
        except Exception:
            log.error("grpc.list_titles_failed", exc_info=True)
            await context.abort(StatusCode.INTERNAL, "title scan failed")
            raise

        return search_pb2.ListTitlesResponse(
            titles=[
                search_pb2.TitleInfo(title=t.title, chunk_count=t.chunk_count)
                for t in listing.titles
            ],
            total_chunks=listing.total_chunks,
            truncated=listing.truncated,
        )

    async def Embed(self, request, context: ServicerContext):  # noqa: N802
        """Encode without storing.

        Also serves the agent's long-term memory store, so exactly one BGE-M3
        exists across the deployment rather than one per service.
        """
        await self._authorize(context)
        texts = list(request.texts)
        if not texts:
            return search_pb2.EmbedResponse(
                model=self._settings.embedding.model_name,
                dimensions=self._dense.dimensions,
            )
        if len(texts) > MAX_EMBED_TEXTS:
            await context.abort(
                StatusCode.INVALID_ARGUMENT,
                f"at most {MAX_EMBED_TEXTS} texts per request, got {len(texts)}",
            )
        try:
            if request.purpose == search_pb2.EMBED_PURPOSE_DOCUMENT:
                dense = await self._dense.embed_documents(texts)
            else:
                dense = [await self._dense.embed_query(t) for t in texts]
            sparse = self._sparse.encode_batch(texts)
        except Exception:
            log.error("grpc.embed_failed", count=len(texts), exc_info=True)
            await context.abort(StatusCode.INTERNAL, "embedding failed")
            raise

        return search_pb2.EmbedResponse(
            dense=[search_pb2.DenseVector(values=v) for v in dense],
            sparse=[search_pb2.SparseVector(indices=s.indices, values=s.values) for s in sparse],
            model=self._settings.embedding.model_name,
            dimensions=self._dense.dimensions,
        )
