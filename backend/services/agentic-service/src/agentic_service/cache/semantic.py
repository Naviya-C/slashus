"""
Semantic response cache.

Two questions asked differently but MEANING the same thing should not cost two
full agent runs -- several tool calls, a large retrieval payload in context, and
a long generation. "What is the water cycle?" and "Can you explain the water
cycle to me?" deserve one execution.

Greetings deliberately do not participate; see ``cache.policy`` for why a cache
keyed on similarity alone turns the tutor into a robot.

WHAT THE KEY MUST INCLUDE, AND WHY
----------------------------------
Similarity of the question is NOT sufficient on its own. The same sentence has
a different correct answer depending on:

  * WHICH USER asked. Answers are grounded in that student's own uploaded
    documents. A cache shared across users is a cross-tenant data leak, not a
    performance optimisation -- so the user id is part of the namespace, not
    part of a score.

  * WHICH DOCUMENTS are in scope. Asking about "the water cycle" with a science
    textbook selected is a different question from asking with a history
    textbook selected.

  * WHETHER THEIR MATERIAL HAS CHANGED. A new upload can change the right
    answer, so an ingest bumps a per-user generation counter and every earlier
    entry stops matching.

Only after all three agree does cosine similarity get consulted.

THRESHOLD
---------
Deliberately high (0.95 by default). Embeddings put "explain photosynthesis"
and "explain respiration" fairly close together; they are opposite processes.
A false hit here is not a slow answer, it is a CONFIDENTLY WRONG answer served
instantly, which for a study tool is the worst failure mode there is. Missing a
legitimate hit merely costs what the system used to cost anyway.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Any

import structlog

from agentic_service.cache.policy import CacheDecision, classify_request, classify_response
from agentic_service.observability.metrics import CACHE_EVENTS, CACHE_LOOKUP

log = structlog.get_logger(__name__)


@dataclass(slots=True)
class CachedAnswer:
    question: str
    answer: str
    tools_used: list[str]
    similarity: float
    age_seconds: float


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def scope_key(
    user_id: str, doc_ids: list[str], document_generation: int, memory_generation: int
) -> str:
    """Namespace component covering everything that changes the right answer."""
    docs = ",".join(sorted(doc_ids)) or "all"
    digest = hashlib.sha256(
        f"{docs}:{document_generation}:{memory_generation}".encode()
    ).hexdigest()[:16]
    return f"semcache:{user_id}:{digest}"


class SemanticCache:
    """Redis-backed. Degrades to a no-op if Redis is unavailable."""

    def __init__(
        self,
        *,
        redis: Any,
        vectors: Any,
        threshold: float = 0.95,
        ttl_seconds: int = 86_400,
        max_entries_per_scope: int = 200,
        enabled: bool = True,
    ) -> None:
        self._redis = redis
        self._vectors = vectors
        self._threshold = threshold
        self._ttl = ttl_seconds
        self._max_entries = max_entries_per_scope
        self._enabled = enabled and redis is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _generations(self, user_id: str) -> tuple[int, int]:
        if not self._enabled:
            return 0, 0
        try:
            document, memory = await self._redis.mget(
                f"semcache:docgen:{user_id}", f"semcache:memgen:{user_id}"
            )
            return int(document or 0), int(memory or 0)
        except Exception:
            return 0, 0

    async def invalidate_user(self, user_id: str) -> None:
        """Called after ingest. Bumping the generation retires every existing
        entry at once, without scanning or deleting keys."""
        
        if not self._enabled:
            return
        try:
            await self._redis.incr(f"semcache:docgen:{user_id}")
            log.info("cache.invalidated", user_id=user_id)
        except Exception:
            log.warning("cache.invalidate_failed", exc_info=True)

    async def invalidate_memory(self, user_id: str) -> None:
        if not self._enabled:
            return
        try:
            await self._redis.incr(f"semcache:memgen:{user_id}")
        except Exception:
            log.warning("cache.memory_invalidate_failed", exc_info=True)

    # --------------------------lookup---------------------------------

    async def lookup(
        self, *, message: str, user_id: str, doc_ids: list[str], has_history: bool
    ) -> CachedAnswer | None:
        """Return a cached answer for a semantically equivalent question."""
        if not self._enabled:
            return None

        decision = classify_request(message, has_history=has_history)
        if decision is not CacheDecision.CACHEABLE:
            CACHE_EVENTS.labels(event="skip", reason=decision.value).inc()
            log.debug("cache.skipped", reason=decision.value)
            return None

        started = time.perf_counter()
        try:
            embedding = await self._embed(message)
            if embedding is None:
                return None

            document_generation, memory_generation = await self._generations(user_id)
            key = scope_key(user_id, doc_ids, document_generation, memory_generation)
            entries = await self._redis.hgetall(key)
        except Exception:
            CACHE_EVENTS.labels(event="error", reason="lookup").inc()
            log.warning("cache.lookup_failed", exc_info=True)
            return None
        finally:
            CACHE_LOOKUP.observe(time.perf_counter() - started)

        if not entries:
            CACHE_EVENTS.labels(event="miss", reason="empty").inc()
            return None

        best: CachedAnswer | None = None
        best_score = 0.0

        for raw in entries.values():
            try:
                record = json.loads(raw)
                score = cosine(embedding, record["embedding"])
            except (ValueError, KeyError, TypeError):
                continue
            if score > best_score:
                best_score = score
                best = CachedAnswer(
                    question=record["question"],
                    answer=record["answer"],
                    tools_used=record.get("tools_used", []),
                    similarity=score,
                    age_seconds=time.time() - record.get("stored_at", 0.0),
                )

        if best is None or best_score < self._threshold:
            CACHE_EVENTS.labels(event="miss", reason="below_threshold").inc()
            log.debug("cache.miss", best_similarity=round(best_score, 3))
            return None

        CACHE_EVENTS.labels(event="hit", reason="semantic").inc()
        log.info(
            "cache.hit",
            similarity=round(best.similarity, 3),
            original=best.question[:60],
            asked=message[:60],
            age_hours=round(best.age_seconds / 3600, 1),
        )
        return best

    # ------------------------------store------------------------------

    async def store(
        self,
        *,
        message: str,
        answer: str,
        user_id: str,
        doc_ids: list[str],
        tools_used: list[str],
        has_history: bool,
        timed_out: bool = False,
    ) -> bool:
        if not self._enabled:
            return False

        if classify_request(message, has_history=has_history) is not CacheDecision.CACHEABLE:
            return False

        decision = classify_response(answer=answer, tools_used=tools_used, timed_out=timed_out)
        if decision is not CacheDecision.CACHEABLE:
            CACHE_EVENTS.labels(event="skip_store", reason=decision.value).inc()
            return False

        try:
            embedding = await self._embed(message)
            if embedding is None:
                return False

            document_generation, memory_generation = await self._generations(user_id)
            key = scope_key(user_id, doc_ids, document_generation, memory_generation)
            field = hashlib.sha256(message.strip().lower().encode()).hexdigest()[:24]
            record = json.dumps(
                {
                    "question": message,
                    "answer": answer,
                    "tools_used": tools_used,
                    "embedding": embedding,
                    "stored_at": time.time(),
                },
                ensure_ascii=False,
            )

            await self._redis.hset(key, field, record)
            await self._redis.expire(key, self._ttl)

            if await self._redis.hlen(key) > self._max_entries:
                await self._evict_oldest(key)

            CACHE_EVENTS.labels(event="store", reason="ok").inc()
            log.debug("cache.stored", question=message[:60])
            return True
        except Exception:
            CACHE_EVENTS.labels(event="error", reason="store").inc()
            log.warning("cache.store_failed", exc_info=True)
            return False

    async def _evict_oldest(self, key: str) -> None:
        entries = await self._redis.hgetall(key)
        aged: list[tuple[float, str]] = []
        for field, raw in entries.items():
            try:
                aged.append((json.loads(raw).get("stored_at", 0.0), field))
            except ValueError:
                aged.append((0.0, field))
        aged.sort()
        for _, field in aged[: max(1, len(aged) - self._max_entries)]:
            await self._redis.hdel(key, field)

    async def _embed(self, text: str) -> list[float] | None:
        """
        Embed via embedding-service.

        Uses the QUERY path so cache keys sit in the same space as retrieval
        queries, and so no second model is loaded in this process.
        """
        try:
            vectors = await self._vectors.embed([text], purpose="query")
        except Exception:
            log.warning("cache.embed_failed", exc_info=True)
            return None
        return vectors[0] if vectors else None
