"""Evaluator data contracts — shared judgement types used by every agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    PASS = "pass"
    REVISE = "revise"
    FAIL = "fail"


@dataclass(slots=True)
class ItemScore:
    """Quality judgement for ONE item (a chunk set, a question, an answer)."""

    item_id: str
    verdict: Verdict
    score: float                     # 0..1
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvaluationReport:
    """Aggregate judgement over a batch of items."""

    passed: bool                     # whole batch acceptable?
    confidence: float
    item_scores: list[ItemScore] = field(default_factory=list)
    summary: str = ""

    def weak_items(self, threshold: float = 0.6) -> list[str]:
        """Item ids that need regeneration (verdict != pass or low score)."""
        return [
            s.item_id for s in self.item_scores
            if s.verdict != Verdict.PASS or s.score < threshold
        ]
