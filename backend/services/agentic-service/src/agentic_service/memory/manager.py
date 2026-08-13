from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from agentic_service.memory.repository import MemoryRepository, StoredMemory
from agentic_service.memory.types import (
    EpisodicMemory,
    MemoryHit,
    MemoryType,
    ProceduralMemory,
    RecalledContext,
    SemanticMemory,
    utcnow,
)

log = structlog.get_logger(__name__)
MAX_SEMANTIC = 6
MAX_EPISODIC = 2
MAX_PROCEDURAL = 8


def _normalise(text: str) -> str:
    return " ".join(re.findall(r"[\w\u0D80-\u0DFF]+", text.casefold()))


def _hash(text: str) -> str:
    return hashlib.sha256(_normalise(text).encode()).hexdigest()


def _similar(a: str, b: str, threshold: float = 0.6) -> bool:
    left, right = set(_normalise(a).split()), set(_normalise(b).split())
    return bool(left and right and len(left & right) / len(left | right) >= threshold)


class MemoryManager:
    def __init__(
        self,
        repository: MemoryRepository,
        *,
        vectors: Any,
        llm: Any = None,
        on_change: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._repo = repository
        self._vectors = vectors
        self._llm = llm
        self._on_change = on_change

    async def _embed(self, text: str, *, purpose: str) -> list[float]:
        vectors = await self._vectors.embed([text], purpose=purpose)
        if not vectors:
            raise RuntimeError("embedding service returned no vector")
        return vectors[0]

    async def recall(self, user_id: str, query: str) -> RecalledContext:
        query = query.strip() or "study preferences"
        try:
            vector = await self._embed(query, purpose="query")
            semantic, episodic, procedural = await asyncio.gather(
                self._repo.search(user_id, MemoryType.SEMANTIC.value, vector, MAX_SEMANTIC),
                self._repo.search(user_id, MemoryType.EPISODIC.value, vector, MAX_EPISODIC),
                self.active_rules(user_id),
            )
        except Exception:
            log.warning("memory.recall_failed", exc_info=True)
            return RecalledContext()
        return RecalledContext(
            semantic=[self._hit(item, MemoryType.SEMANTIC) for item in semantic],
            episodic=[self._hit(item, MemoryType.EPISODIC) for item in episodic],
            procedural=procedural,
        )

    @staticmethod
    def _hit(item: StoredMemory, kind: MemoryType) -> MemoryHit:
        payload = {k: v for k, v in item.payload.items() if not k.startswith("_")}
        if kind is MemoryType.EPISODIC:
            try:
                text = EpisodicMemory.model_validate(payload).as_exemplar()
            except ValueError:
                text = item.searchable_text
        else:
            text = str(payload.get("content") or payload.get("instruction") or item.searchable_text)
        return MemoryHit(key=item.key, kind=kind, text=text, score=item.score, payload=payload)

    async def active_rules(self, user_id: str) -> list[ProceduralMemory]:
        items = await self._repo.list_active(user_id, MemoryType.PROCEDURAL.value, MAX_PROCEDURAL)
        rules: list[ProceduralMemory] = []
        for item in items:
            try:
                rule = ProceduralMemory.model_validate(item.payload)
            except ValueError:
                continue
            if rule.active:
                rules.append(rule)
        return rules

    async def _changed(self, user_id: str) -> None:
        if self._on_change is not None:
            await self._on_change(user_id)

    async def remember_fact(self, user_id: str, memory: SemanticMemory) -> str:
        vector = await self._embed(memory.content, purpose="document")
        key = await self._repo.put(
            user_id,
            MemoryType.SEMANTIC.value,
            _hash(memory.content),
            memory.content,
            memory.model_dump(mode="json"),
            vector,
        )
        await self._changed(user_id)
        return key

    async def record_episode(self, user_id: str, episode: EpisodicMemory) -> str:
        text = f"{episode.situation}\n{episode.action}\n{episode.outcome}\n{episode.lesson}"
        vector = await self._embed(text, purpose="document")
        key = await self._repo.put(
            user_id,
            MemoryType.EPISODIC.value,
            _hash(text),
            text,
            episode.model_dump(mode="json"),
            vector,
        )
        await self._changed(user_id)
        return key

    async def upsert_rule(self, user_id: str, rule: ProceduralMemory) -> str:
        vector = await self._embed(rule.instruction, purpose="document")
        existing = await self._repo.search(
            user_id, MemoryType.PROCEDURAL.value, vector, MAX_PROCEDURAL
        )
        for item in existing:
            try:
                current = ProceduralMemory.model_validate(item.payload)
            except ValueError:
                continue
            if current.scope == rule.scope and _similar(current.instruction, rule.instruction):
                rule.version = current.version + 1
                rule.updated_at = utcnow()
                key = await self._repo.put(
                    user_id,
                    MemoryType.PROCEDURAL.value,
                    _hash(rule.instruction),
                    rule.instruction,
                    rule.model_dump(mode="json"),
                    vector,
                    key=item.key,
                    version=rule.version,
                    active=rule.active,
                )
                await self._changed(user_id)
                return key
        key = await self._repo.put(
            user_id,
            MemoryType.PROCEDURAL.value,
            _hash(rule.instruction),
            rule.instruction,
            rule.model_dump(mode="json"),
            vector,
            version=rule.version,
            active=rule.active,
        )
        await self._changed(user_id)
        return key

    async def erase(self, user_id: str, kind: str) -> int:
        if kind not in {"semantic", "episodic", "procedural"}:
            raise ValueError(f"unknown memory type {kind!r}")
        count = await self._repo.erase_kind(user_id, kind)
        if count:
            await self._changed(user_id)
        return count

    async def consolidate(
        self,
        user_id: str,
        *,
        conversation: list[dict[str, str]],
        tools_used: list[str],
        subject: str = "",
    ) -> None:
        if self._llm is None or len(conversation) < 2:
            return
        from agentic_service.prompts.pool import get_prompt_pool

        transcript = "\n".join(
            f"{turn['role']}: {turn['content'][:1000]}" for turn in conversation[-2:]
        )
        try:
            data = await self._llm.ainvoke_json(
                get_prompt_pool().render(
                    "CONSOLIDATE",
                    transcript=transcript,
                    tools_used=", ".join(tools_used) or "(none)",
                ),
                label="consolidate",
            )
        except Exception:
            log.warning("memory.consolidation_failed", exc_info=True)
            return
        if episode_data := data.get("episode"):
            try:
                await self.record_episode(
                    user_id,
                    EpisodicMemory.model_validate(
                        {**episode_data, "subject": episode_data.get("subject", subject)}
                    ),
                )
            except ValueError:
                log.warning("memory.malformed_episode")
        for rule_data in data.get("rules", []) or []:
            try:
                await self.upsert_rule(user_id, ProceduralMemory.model_validate(rule_data))
            except ValueError:
                log.warning("memory.malformed_rule")
        for fact_data in data.get("facts", []) or []:
            try:
                await self.remember_fact(user_id, SemanticMemory.model_validate(fact_data))
            except ValueError:
                log.warning("memory.malformed_fact")
