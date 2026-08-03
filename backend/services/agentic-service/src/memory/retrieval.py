"""
memory/retrieval.py
===================

What the last search did, so the next turn can decide not to repeat it.

"Explain more", "continue", "give another example", "summarise that" — none of
those describe a topic. Embedding them and searching returns whatever is
nearest to the words "explain more" in a Sinhala textbook, which is nothing
useful. The material the student means is the material we already found.

Reusing it is faster, cheaper, and — the part that matters — CORRECT, because
a fresh search on a contentless follow-up actively replaces good context with
bad.

WHAT IS STORED AND WHAT IS NOT
------------------------------
Chunk text IS stored, and this is the one place it is. Reuse is impossible
without it, and the alternative (store ids, re-fetch by id) is a second round
trip to get back something already held. It lives in Redis under a session
key with a TTL and never leaves the server.

WHO DECIDES TO REUSE
--------------------
Not this module. It stores and returns; the LLM decides in the retrieval plan
whether `reuse_previous` is right for this query. That is the whole point of
the rebase — a `if "more" in query` heuristic here would be the application
deciding, and it would be wrong for every phrasing nobody thought of.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# Enough to answer a follow-up without re-searching. Beyond this the Redis
# value gets large and the saving stops being worth it.
_MAX_STORED_CHUNKS = 16


@dataclass
class RetrievalSnapshot:
    query: str = ""
    keywords: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    lesson_titles: list[str] = field(default_factory=list)
    doc_ids: list[str] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)

    def is_usable(self) -> bool:
        return bool(self.chunks)

    def describe(self) -> str:
        """One line for a decision prompt.

        Deliberately not the chunk text. The planning LLM needs to know WHAT
        was found to decide whether it is still relevant; giving it the full
        passages would triple the prompt and invite it to answer from them
        instead of planning.
        """
        if not self.is_usable():
            return "(nothing retrieved yet in this session)"
        titles = ", ".join(sorted({c.get("title", "") for c in self.chunks if c.get("title")}))
        return (f"previous search: {self.query!r} -> {len(self.chunks)} chunks"
                f"{' from: ' + titles if titles else ''}")


class RetrievalMemory:
    def __init__(self, scratch) -> None:
        self._scratch = scratch

    def load(self, user_id: UUID, session_id: str) -> RetrievalSnapshot:
        raw = self._scratch.get(user_id, session_id, "retrieval")
        if not raw:
            return RetrievalSnapshot()
        try:
            return RetrievalSnapshot(**raw)
        except TypeError:
            # Shape changed across a deploy. Treat as no memory rather than
            # crashing the turn on a field that no longer exists.
            logger.warning("stale retrieval snapshot discarded")
            return RetrievalSnapshot()

    def save(self, user_id: UUID, session_id: str, snapshot: RetrievalSnapshot) -> None:
        self._scratch.set(user_id, session_id, "retrieval", {
            "query": snapshot.query,
            "keywords": snapshot.keywords,
            "filters": snapshot.filters,
            "lesson_titles": snapshot.lesson_titles,
            "doc_ids": snapshot.doc_ids,
            "chunks": snapshot.chunks[:_MAX_STORED_CHUNKS],
            "plan": snapshot.plan,
        })
