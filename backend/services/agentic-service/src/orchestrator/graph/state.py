"""Graph state type for the orchestrator."""

from __future__ import annotations

from typing import Any, TypedDict
from uuid import UUID

 
class GraphState(TypedDict, total=False):
    user_id: UUID  
    session_id: str
    message: str
    intent: str
    steps: list[str]
    method: str
    data: dict[str, Any]
    errors: list[str]
    reply: str
