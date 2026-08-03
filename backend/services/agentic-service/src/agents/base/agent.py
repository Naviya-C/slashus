"""Agent base class, capability enum, and the shared run context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID


class Capability(str, Enum):
    """What an agent can do. Intents map to capabilities; capabilities to
    agents. Add new capabilities as the system grows."""

    RETRIEVE = "retrieve"
    GENERATE = "generate"          # questions, answers, summaries, flashcards, explanations
    MARK = "mark"                  # auto-grading student work
    # future: SUMMARIZE, EXPLAIN, TRANSLATE, FLASHCARDS, ...


@dataclass
class AgentContext:
    """Shared bag threaded through one orchestrated run. Agents read what
    earlier agents wrote and add their own output — this is how chaining
    works (retrieval writes `chunks`; qgen reads them)."""

    query: str
    user_id: UUID
    session_id: str = "default"
    language: str = "si"
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def put(self, **kwargs: Any) -> None:
        self.data.update(kwargs)


class Agent(ABC):
    """Base for every agent. Subclass, set name + capability, implement run."""

    name: str = ""
    capability: Capability

    @abstractmethod
    def run(self, ctx: AgentContext) -> None:
        """Do the work; read from and write to ctx.data. Recoverable issues
        should append to ctx.errors, not raise."""
        raise NotImplementedError
