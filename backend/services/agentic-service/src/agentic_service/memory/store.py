"""
Framework store used by LangGraph internals.

Durable semantic, episodic and procedural memories live in PostgreSQL/pgvector
through ``memory.repository``. This store intentionally has no vector index so
there is one long-term-memory source of truth.
"""

from __future__ import annotations

from typing import Any

import structlog
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

log = structlog.get_logger(__name__)


async def build_store(
    *, redis_url: str | None, vectors: Any, dimensions: int
) -> tuple[BaseStore, Any]:
    """
    Return (store, closer).

    Redis-backed in any real deployment. The in-memory fallback is explicitly a
    local-development path: with more than one replica it means a student's
    memories exist on whichever container happened to serve the turn that
    created them.
    """
    if not redis_url:
        log.warning(
            "store.in_memory",
            detail="no REDIS_URL; long-term memory is per-process and will not survive restart",
        )
        return InMemoryStore(), None

    try:
        from langgraph.store.redis.aio import AsyncRedisStore

        manager = AsyncRedisStore.from_conn_string(redis_url)
        store = await manager.__aenter__()
        await store.setup()
        log.info("store.redis", dimensions=dimensions)
        return store, manager
    except Exception:
        log.error("store.redis_failed_falling_back", exc_info=True)
        return InMemoryStore(), None
