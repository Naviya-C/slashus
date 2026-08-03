"""Retrieval agent data contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Understanding:
    raw_query: str
    normalized_query: str
    language: str = "si"
    question_count: int = 1
    complexity: str = "simple"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Plan:
    chunk_budget: int
    metadata_filters: dict[str, Any] = field(default_factory=dict)
    enable_reranking: bool = True


@dataclass(slots=True)
class Evaluation:
    sufficient: bool
    confidence: float
    next_action: str
    rewritten_query: str | None = None

    @property
    def quality(self) -> float:
        return (1.0 if self.sufficient else 0.0) + self.confidence
