"""The four memory types, as a domain model.

The taxonomy is the standard cognitive one, mapped onto what a tutoring agent
actually needs. What matters is that each type has a DIFFERENT lifetime, a
DIFFERENT write path, and a DIFFERENT read path -- otherwise "four memory
types" is one store with four labels on it.

    ┌──────────────┬─────────────┬──────────────────┬─────────────────────┐
    │ Type         │ Lifetime    │ Written by       │ Read by             │
    ├──────────────┼─────────────┼──────────────────┼─────────────────────┤
    │ WORKING      │ one turn    │ the graph itself │ every model call    │
    │              │ (+ thread)  │ (checkpointer)   │ (message history)   │
    ├──────────────┼─────────────┼──────────────────┼─────────────────────┤
    │ SEMANTIC     │ permanent   │ agent tool call  │ recalled by vector  │
    │              │             │ + background     │ search on the turn  │
    ├──────────────┼─────────────┼──────────────────┼─────────────────────┤
    │ EPISODIC     │ permanent   │ background       │ recalled as few-shot│
    │              │             │ consolidation    │ exemplars           │
    ├──────────────┼─────────────┼──────────────────┼─────────────────────┤
    │ PROCEDURAL   │ permanent,  │ reflection over  │ injected into the   │
    │              │ versioned   │ feedback         │ system prompt       │
    └──────────────┴─────────────┴──────────────────┴─────────────────────┘

WORKING memory lives in the LangGraph checkpointer. The other three are durable
PostgreSQL/pgvector rows and every query includes the authenticated user id.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class MemoryType(StrEnum):
    WORKING = "working"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


# Legacy namespace helpers retained for import compatibility. New durable
# memory is stored through memory.repository, not LangGraph BaseStore.


def semantic_ns(user_id: str) -> tuple[str, ...]:
    """Facts about this student. Namespaced per user."""
    return ("memories", user_id, MemoryType.SEMANTIC.value)


def episodic_ns(user_id: str) -> tuple[str, ...]:
    """Past tutoring episodes for this student."""
    return ("memories", user_id, MemoryType.EPISODIC.value)


def procedural_ns(user_id: str) -> tuple[str, ...]:
    """Learned instructions for how to tutor THIS student."""
    return ("memories", user_id, MemoryType.PROCEDURAL.value)


# --- schemas ---------------------------------------------------------------
#
# Typed rather than free-text strings. The agent writes these through a tool,
# and a schema is what lets the model be told precisely what a "fact" is versus
# a "misconception" -- untyped memory degenerates into a pile of paraphrased
# conversation, which then pollutes every subsequent recall.


class SemanticMemory(BaseModel):
    """A durable fact about the student or their material.

    Examples: "prefers explanations in Sinhala", "is studying for O/L history",
    "confuses the Anuradhapura and Polonnaruwa periods".
    """

    model_config = ConfigDict(extra="ignore")

    content: str = Field(..., description="The fact, stated in one sentence.")
    category: Literal["preference", "goal", "background", "misconception", "fact"] = "fact"
    subject: str = Field("", description="Lesson or topic this relates to, if any.")
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    source: Literal["stated", "inferred"] = "inferred"
    updated_at: datetime = Field(default_factory=utcnow)


class EpisodicMemory(BaseModel):
    """A completed tutoring episode, stored so it can be reused as an exemplar.

    Episodic memory is what lets the agent say "last time this student asked
    about the water cycle, breaking it into stages worked" -- and it is stored
    with the OUTCOME, because an episode with no outcome teaches nothing.
    """

    model_config = ConfigDict(extra="ignore")

    situation: str = Field(..., description="What the student asked and the context.")
    action: str = Field(..., description="What the agent did, including tools used.")
    outcome: str = Field(..., description="How it went, and how we know.")
    lesson: str = Field("", description="The transferable takeaway, if any.")
    success: bool = True
    subject: str = ""
    occurred_at: datetime = Field(default_factory=utcnow)

    def as_exemplar(self) -> str:
        verdict = "WORKED" if self.success else "DID NOT WORK"
        return (
            f"Situation: {self.situation}\n"
            f"Action: {self.action}\n"
            f"Outcome ({verdict}): {self.outcome}"
            + (f"\nLesson: {self.lesson}" if self.lesson else "")
        )


class ProceduralMemory(BaseModel):
    """A learned rule about HOW to tutor this student.

    This is the memory type that actually changes the agent's behaviour: its
    contents are injected into the system prompt, so a rule here rewrites how
    every subsequent turn is handled. Versioned because that power cuts both
    ways -- a bad rule silently degrades every response until someone notices,
    and you need to be able to see what changed and when.
    """

    model_config = ConfigDict(extra="ignore")

    instruction: str = Field(..., description="An imperative rule, one sentence.")
    scope: Literal["global", "explanation", "quiz", "marking"] = "global"
    rationale: str = Field("", description="The evidence that produced this rule.")
    version: int = 1
    active: bool = True
    updated_at: datetime = Field(default_factory=utcnow)


class MemoryHit(BaseModel):
    """A recalled item, flattened for prompt rendering."""

    model_config = ConfigDict(extra="allow")

    key: str
    kind: MemoryType
    text: str
    score: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)


class RecalledContext(BaseModel):
    """Everything recalled for one turn, ready to render into the prompt."""

    semantic: list[MemoryHit] = Field(default_factory=list)
    episodic: list[MemoryHit] = Field(default_factory=list)
    procedural: list[ProceduralMemory] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.semantic or self.episodic or self.procedural)

    def render(self) -> str:
        """Render for injection into the system prompt.

        Kept compact on purpose. Recall is injected on EVERY turn, so verbose
        formatting here is a tax paid on every model call for the whole session.
        """
        if self.is_empty():
            return ""

        blocks: list[str] = []

        if self.procedural:
            rules = "\n".join(f"- {p.instruction}" for p in self.procedural)
            blocks.append("HOW TO WORK WITH THIS STUDENT (learned from experience):\n" + rules)

        if self.semantic:
            facts = "\n".join(f"- {m.text}" for m in self.semantic)
            blocks.append("WHAT YOU KNOW ABOUT THIS STUDENT:\n" + facts)

        if self.episodic:
            episodes = "\n\n".join(m.text for m in self.episodic)
            blocks.append("SIMILAR SITUATIONS YOU HAVE HANDLED BEFORE:\n" + episodes)

        return "\n\n".join(blocks)
