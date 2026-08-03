"""
memory/working.py
=================

Short-term memory for ONE graph execution. Dies with the request.

This is the scratchpad every node reads and writes: the query, the route, the
plan, the chunks, the answer, the tool outputs, the intermediate reasoning.

WHY A CLASS AND NOT A DICT
--------------------------
Two reasons, both learned the expensive way.

`steps` records every decision and every tool call with its timing. When a
student gets a wrong answer, the question is always "which decision was
wrong?" — and a dict gives you the final state with no way to reconstruct how
it got there. This makes the reasoning trace a first-class value rather than
something scattered across log lines.

`tool_calls` is capped. An agent loop that decides to search, evaluate, and
search again has no natural stopping point if a decision keeps returning the
same next action, and an uncapped loop bills real money in a tight circle.
The cap is enforced HERE rather than in the loop, because every caller would
otherwise have to remember to enforce it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Step:
    """One decision or one tool execution."""
    kind: str                      # "decision" | "tool"
    name: str
    detail: dict[str, Any] = field(default_factory=dict)
    ms: float = 0.0


@dataclass
class WorkingMemory:
    query: str
    user_id: str
    session_id: str
    doc_ids: list[str] = field(default_factory=list)

    # --- what the LLM decided --------------------------------------------
    route: str = ""
    language: str = "si"
    understanding: dict[str, Any] = field(default_factory=dict)
    retrieval_plan: dict[str, Any] = field(default_factory=dict)
    quiz_plan: dict[str, Any] = field(default_factory=dict)

    # --- what the tools returned -----------------------------------------
    chunks: list[dict[str, Any]] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    tool_calls: int = 0

    # --- what came out ----------------------------------------------------
    answer: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    practice_set_id: str | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    clarification: str = ""
    reason: str | None = None

    # --- how it got there -------------------------------------------------
    steps: list[Step] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    reused_retrieval: bool = False

    max_tool_calls: int = 8
    _started: float = field(default_factory=time.perf_counter)

    # ------------------------------------------------------------------

    def record(self, kind: str, name: str, ms: float = 0.0, **detail: Any) -> None:
        self.steps.append(Step(kind=kind, name=name, detail=detail, ms=ms))

    def budget_left(self) -> bool:
        return self.tool_calls < self.max_tool_calls

    def spend(self) -> None:
        self.tool_calls += 1

    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._started) * 1000

    def trace(self) -> list[dict[str, Any]]:
        """The reasoning trace, as the API returns it.

        Deliberately excludes chunk TEXT. Chunks are full passages of
        copyrighted textbooks; a debug field that ships them to the browser is
        a copyright leak wearing an observability hat.
        """
        return [
            {"kind": s.kind, "name": s.name, "ms": round(s.ms, 1), **s.detail}
            for s in self.steps
        ]
