"""
tools/memory_tools.py
=====================

Memory as tools, so reuse is an ACTION the agent takes rather than something
Python does behind it.

`reuse_previous_retrieval` is the one that matters. "Explain more", "continue",
"give another example" describe no topic at all — embedding them returns
whatever sits nearest the words "explain more" in a Sinhala textbook, which is
noise. The material the student means is the material already found.

The agent decides when this applies, in the retrieval plan. Deliberately not a
keyword check here: `if "more" in query` fails on every phrasing nobody
anticipated, and Sinhala has many.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from tools.base import Tool, ToolError, ToolRegistry

logger = logging.getLogger(__name__)


def register_memory_tools(registry: ToolRegistry, store) -> None:

    def reuse_previous_retrieval(*, user_id: UUID, session_id: str) -> dict[str, Any]:
        snapshot = store.retrieval.load(user_id, session_id)
        if not snapshot.is_usable():
            # Returned as a failure so the agent can fall back to searching.
            # Silently returning zero chunks would look like a corpus with
            # nothing in it, and the agent would tell the student to upload.
            raise ToolError("no previous retrieval in this session")
        return {"chunks": snapshot.chunks, "query": snapshot.query,
                "lesson_titles": snapshot.lesson_titles}

    def recall_previous_questions(*, user_id: UUID, session_id: str) -> dict[str, Any]:
        """What the student has already been asked, so a continuation differs.

        Without this, "give me 5 more" produces five questions that overlap
        heavily with the first five — the model has no way to know what it
        already generated.
        """
        if store.repo is None:
            return {"questions": []}
        prior = store.conversation.load(user_id, session_id)
        return {"questions": prior.preferences.get("asked", []),
                "active_topic": prior.active_topic}

    registry.add(Tool(
        name="reuse_previous_retrieval",
        description=(
            "Return the chunks found earlier in this session, without "
            "searching. Use for follow-ups that name no new topic — "
            "'explain more', 'continue', 'another example', 'summarise that'"),
        args={},
        run=reuse_previous_retrieval,
    ))
    registry.add(Tool(
        name="recall_previous_questions",
        description="What this student has already been asked in this session",
        args={},
        run=recall_previous_questions,
    ))
