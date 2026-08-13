from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentic_service.adapters.models_db import AgentMemory, utcnow


@dataclass(slots=True)
class StoredMemory:
    key: str
    payload: dict[str, Any]
    searchable_text: str
    score: float = 0.0
    version: int = 1
    active: bool = True


class MemoryRepository(Protocol):
    async def search(
        self, user_id: str, kind: str, embedding: list[float], limit: int
    ) -> list[StoredMemory]: ...

    async def list_active(self, user_id: str, kind: str, limit: int) -> list[StoredMemory]: ...

    async def put(
        self,
        user_id: str,
        kind: str,
        content_hash: str,
        searchable_text: str,
        payload: dict[str, Any],
        embedding: list[float],
        *,
        key: str | None = None,
        version: int = 1,
        active: bool = True,
    ) -> str: ...

    async def erase_kind(self, user_id: str, kind: str) -> int: ...


class SqlMemoryRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def search(
        self, user_id: str, kind: str, embedding: list[float], limit: int
    ) -> list[StoredMemory]:
        distance = AgentMemory.embedding.cosine_distance(embedding).label("distance")
        async with self._sf() as db:
            rows = (
                await db.execute(
                    select(AgentMemory, distance)
                    .where(
                        AgentMemory.user_id == UUID(user_id),
                        AgentMemory.kind == kind,
                        AgentMemory.active.is_(True),
                    )
                    .order_by(distance)
                    .limit(limit)
                )
            ).all()
        return [
            StoredMemory(
                key=str(row.id),
                payload=dict(row.payload),
                searchable_text=row.searchable_text,
                score=max(0.0, 1.0 - float(dist)),
                version=row.version,
                active=row.active,
            )
            for row, dist in rows
        ]

    async def list_active(self, user_id: str, kind: str, limit: int) -> list[StoredMemory]:
        async with self._sf() as db:
            rows = list(
                await db.scalars(
                    select(AgentMemory)
                    .where(
                        AgentMemory.user_id == UUID(user_id),
                        AgentMemory.kind == kind,
                        AgentMemory.active.is_(True),
                    )
                    .order_by(AgentMemory.updated_at.desc())
                    .limit(limit)
                )
            )
        return [
            StoredMemory(
                key=str(row.id),
                payload=dict(row.payload),
                searchable_text=row.searchable_text,
                version=row.version,
                active=row.active,
            )
            for row in rows
        ]

    async def put(
        self,
        user_id: str,
        kind: str,
        content_hash: str,
        searchable_text: str,
        payload: dict[str, Any],
        embedding: list[float],
        *,
        key: str | None = None,
        version: int = 1,
        active: bool = True,
    ) -> str:
        async with self._sf() as db, db.begin():
            row = None
            if key:
                row = await db.scalar(
                    select(AgentMemory).where(
                        AgentMemory.id == UUID(key), AgentMemory.user_id == UUID(user_id)
                    )
                )
            if row is None:
                row = await db.scalar(
                    select(AgentMemory).where(
                        AgentMemory.user_id == UUID(user_id),
                        AgentMemory.kind == kind,
                        AgentMemory.content_hash == content_hash,
                    )
                )
            if row is None:
                row = AgentMemory(
                    id=uuid4(),
                    user_id=UUID(user_id),
                    kind=kind,
                    content_hash=content_hash,
                    searchable_text=searchable_text,
                    payload=payload,
                    embedding=embedding,
                    version=version,
                    active=active,
                )
                db.add(row)
            else:
                row.content_hash = content_hash
                row.searchable_text = searchable_text
                row.payload = payload
                row.embedding = embedding
                row.version = max(row.version, version)
                row.active = active
                row.updated_at = utcnow()
            await db.flush()
            return str(row.id)

    async def erase_kind(self, user_id: str, kind: str) -> int:
        async with self._sf() as db, db.begin():
            result = await db.execute(
                delete(AgentMemory).where(
                    AgentMemory.user_id == UUID(user_id), AgentMemory.kind == kind
                )
            )
            return int(result.rowcount or 0)


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str], StoredMemory] = {}

    async def search(
        self, user_id: str, kind: str, embedding: list[float], limit: int
    ) -> list[StoredMemory]:
        items = [
            v for (u, k, _), v in self._items.items() if u == user_id and k == kind and v.active
        ]
        return items[:limit]

    async def list_active(self, user_id: str, kind: str, limit: int) -> list[StoredMemory]:
        return await self.search(user_id, kind, [], limit)

    async def put(
        self,
        user_id: str,
        kind: str,
        content_hash: str,
        searchable_text: str,
        payload: dict[str, Any],
        embedding: list[float],
        *,
        key: str | None = None,
        version: int = 1,
        active: bool = True,
    ) -> str:
        existing_key = next(
            (
                item_key
                for (u, k, item_key), item in self._items.items()
                if u == user_id and k == kind and item.payload.get("_content_hash") == content_hash
            ),
            None,
        )
        target = key or existing_key or str(uuid4())
        stored_payload = dict(payload)
        stored_payload["_content_hash"] = content_hash
        self._items[(user_id, kind, target)] = StoredMemory(
            target, stored_payload, searchable_text, 1.0, version, active
        )
        return target

    async def erase_kind(self, user_id: str, kind: str) -> int:
        keys = [key for key in self._items if key[0] == user_id and key[1] == kind]
        for key in keys:
            del self._items[key]
        return len(keys)
