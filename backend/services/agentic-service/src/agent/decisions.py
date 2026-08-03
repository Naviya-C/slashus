"""
agent/decisions.py
==================

The shapes the LLM decides in, and the validation that makes them safe to act
on.

WHY EVERY FIELD HAS A FALLBACK
------------------------------
An LLM returns JSON that is usually right. `count: "five"`, `budget: 900`,
`route: "RETRIEVE_AND_GENERATE"` when the options were lowercase,
`needs_clarification: "no"` as a string — all of these arrive in production,
and none of them should be a 500.

So each `from_json` coerces rather than validates-and-raises. The fallback is
always the SAFE direction, not the convenient one:

  * unknown route      -> answer, not questions. An unwanted explanation is
                          mildly annoying; an unwanted practice set opens a
                          panel the student did not ask for and buries their
                          actual question.
  * unparseable budget -> the default, never the model's number unclamped
  * clarification flag  -> false. Asking a clarifying question the student did
                          not need is a wasted turn; the agent should try.

WHY THIS IS NOT PYDANTIC
------------------------
Pydantic would raise on the first bad field and discard the eleven good ones.
Here a malformed `count` costs the default count, not the whole decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The routes the agent may take. Kept small on purpose: every extra route is
# another branch the model gets to be wrong about, and "summarise" and
# "explain" are the same execution path with a different prompt style.
ROUTES = ("answer", "questions", "mark", "clarify", "chat")

_QTYPES = ("mcq", "true_false", "short", "structured", "essay")
_DIFFICULTIES = ("easy", "medium", "hard")

_MAX_BUDGET = 40
_MAX_COUNT = 10


def _str(value: Any, default: str = "") -> str:
    return str(value).strip() if value not in (None, "") else default


def _bool(value: Any, default: bool = False) -> bool:
    """Handles true, "true", "yes", 1 — all of which the model produces."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "y", "1")
    return default


def _int(value: Any, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(int(value), high))
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float) -> float:
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return default


def _list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _choice(value: Any, options: tuple[str, ...], default: str) -> str:
    got = str(value or "").strip().lower()
    return got if got in options else default


# ---------------------------------------------------------------------------

@dataclass
class Understanding:
    """What the student wants, and whether we can act on it yet."""

    intent: str = "answer"
    route: str = "answer"
    normalized_query: str = ""
    is_followup: bool = False
    continues_topic: bool = False
    topic: str = ""
    needs_clarification: bool = False
    clarification_question: str = ""
    confidence: float = 0.5
    reasoning: str = ""
    preferences: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict, fallback_query: str) -> Understanding:
        route = _choice(data.get("route"), ROUTES, "answer")
        needs = _bool(data.get("needs_clarification"), False)
        question = _str(data.get("clarification_question"))

        # A clarification route with no question to ask would return an empty
        # bubble. Treat it as "the model flagged ambiguity but could not say
        # what was ambiguous", which is not actionable — proceed instead.
        if needs and not question:
            needs = False
        if needs:
            route = "clarify"

        return cls(
            intent=_str(data.get("intent"), route),
            route=route,
            normalized_query=_str(data.get("normalized_query"), fallback_query),
            is_followup=_bool(data.get("is_followup")),
            continues_topic=_bool(data.get("continues_topic")),
            topic=_str(data.get("topic")),
            needs_clarification=needs,
            clarification_question=question,
            confidence=_float(data.get("confidence"), 0.5),
            reasoning=_str(data.get("reasoning")),
            preferences=data.get("preferences") if isinstance(
                data.get("preferences"), dict) else {},
        )


@dataclass
class RetrievalPlan:
    """How to find the material — or whether to look at all."""

    should_retrieve: bool = True
    reuse_previous: bool = False
    search_query: str = ""
    keywords: list[str] = field(default_factory=list)
    lesson_title_hint: str = ""
    lesson_title: str = ""          # filled in later, from the REAL list
    metadata_filters: dict[str, Any] = field(default_factory=dict)
    budget: int = 12
    use_doc_filter: bool = True
    use_conversation_context: bool = False
    reasoning: str = ""

    @classmethod
    def from_json(cls, data: dict, fallback_query: str) -> RetrievalPlan:
        filters = data.get("metadata_filters")
        return cls(
            should_retrieve=_bool(data.get("should_retrieve"), True),
            reuse_previous=_bool(data.get("reuse_previous")),
            search_query=_str(data.get("search_query"), fallback_query),
            keywords=_list(data.get("keywords")),
            lesson_title_hint=_str(data.get("lesson_title_hint")),
            metadata_filters=filters if isinstance(filters, dict) else {},
            budget=_int(data.get("budget"), 12, 1, _MAX_BUDGET),
            use_doc_filter=_bool(data.get("use_doc_filter"), True),
            use_conversation_context=_bool(data.get("use_conversation_context")),
            reasoning=_str(data.get("reasoning")),
        )


@dataclass
class RetrievalVerdict:
    """Is what we found enough, and if not, what next."""

    sufficient: bool = True
    confidence: float = 0.5
    missing_concepts: list[str] = field(default_factory=list)
    next_action: str = "proceed"     # proceed | rewrite | widen | give_up
    rewritten_query: str = ""
    reasoning: str = ""

    @classmethod
    def from_json(cls, data: dict) -> RetrievalVerdict:
        action = _choice(data.get("next_action"),
                         ("proceed", "rewrite", "widen", "give_up"), "proceed")
        rewritten = _str(data.get("rewritten_query"))

        # A rewrite instruction with no rewritten query would re-run the
        # identical search, spend a call, and get the identical result.
        if action == "rewrite" and not rewritten:
            action = "widen"

        return cls(
            sufficient=_bool(data.get("sufficient"), True),
            confidence=_float(data.get("confidence"), 0.5),
            missing_concepts=_list(data.get("missing_concepts")),
            next_action=action,
            rewritten_query=rewritten,
            reasoning=_str(data.get("reasoning")),
        )


@dataclass
class QuizPlan:
    """What kind of practice set, and how much of it."""

    qtype: str = "mcq"
    count: int = 5
    difficulty: str = "medium"
    bloom_level: str = "understand"
    topics: list[str] = field(default_factory=list)
    include_explanations: bool = True
    reasoning: str = ""

    @classmethod
    def from_json(cls, data: dict) -> QuizPlan:
        return cls(
            qtype=_choice(data.get("question_type"), _QTYPES, "mcq"),
            count=_int(data.get("count"), 5, 1, _MAX_COUNT),
            difficulty=_choice(data.get("difficulty"), _DIFFICULTIES, "medium"),
            bloom_level=_str(data.get("bloom_level"), "understand"),
            topics=_list(data.get("topics")),
            include_explanations=_bool(data.get("include_explanations"), True),
            reasoning=_str(data.get("reasoning")),
        )


@dataclass
class AnswerPlan:
    """Style hints for a prose answer. Small, because the ANSWER prompt does
    the real work — this only carries what the CONVERSATION implies and the
    prompt cannot know."""

    style: str = ""
    include_citations: bool = True
    reasoning: str = ""

    @classmethod
    def from_json(cls, data: dict) -> AnswerPlan:
        return cls(
            style=_str(data.get("style")),
            include_citations=_bool(data.get("include_citations"), True),
            reasoning=_str(data.get("reasoning")),
        )
