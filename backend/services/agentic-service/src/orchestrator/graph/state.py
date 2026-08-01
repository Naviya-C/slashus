"""Graph state type for the orchestrator."""

from __future__ import annotations

from typing import Any, TypedDict
from uuid import UUID


class GraphState(TypedDict, total=False):
    user_id: UUID
    session_id: str
    message: str
    doc_ids: list[str]
    intent: str
    steps: list[str]
    method: str
    data: dict[str, Any]
    errors: list[str]
    reply: str
    # Set when a request cannot be served (no documents, nothing relevant).
    # Carried through to the API, which turns it into a specific user-facing
    # message rather than a generic failure.
    reason: str | None
