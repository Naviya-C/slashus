"""
agent/decisions.py
==================

The shapes the LLM decides in — pydantic models with COERCING validators.

WHY COERCE RATHER THAN RAISE
----------------------------
An LLM returns JSON that is usually right. `count: "five"`, `budget: 900`,
`route: "RETRIEVE_AND_GENERATE"` when the options were lowercase,
`needs_clarification: "no"` as a string — all of these arrive in production.

Plain pydantic raises on the first bad field and discards the eleven good
ones. Here a malformed `count` costs the default count, not the whole
decision. So every model uses `model_validator(mode="before")` to clean the
payload, and the graph never sees a ValidationError from a model that merely
got one field wrong.

The fallback is always the SAFE direction, not the convenient one:

  * unknown route      -> answer, not questions. An unwanted explanation is
                          mildly annoying; an unwanted practice set opens a
                          panel the student did not ask for and buries their
                          actual question.
  * unparseable budget -> the default, never the model's number unclamped
  * clarification flag -> false. Asking a clarifying question the student did
                          not need wastes a turn; the agent should try.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# The routes the agent may take. Small on purpose: every extra route is
# another branch the model gets to be wrong about, and "summarise" and
# "explain" are the same execution path with a different prompt style.
Route = Literal["answer", "questions", "mark", "clarify", "chat"]
QType = Literal["mcq", "true_false", "short", "structured", "essay"]
Difficulty = Literal["easy", "medium", "hard"]
NextAction = Literal["proceed", "rewrite", "widen", "give_up"]

MAX_BUDGET = 40
MAX_COUNT = 10


# ---------------------------------------------------------------------------
# coercion helpers
# ---------------------------------------------------------------------------

def _as_bool(value: Any, default: bool = False) -> bool:
    """true, "true", "yes", 1 — the model produces all of them."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "y", "1")
    return default


def _as_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(int(value), high))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    return str(value).strip() if value not in (None, "") else default


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _one_of(value: Any, options: tuple[str, ...], default: str) -> str:
    got = str(value or "").strip().lower()
    return got if got in options else default


class _Decision(BaseModel):
    """Base: ignore unknown keys rather than rejecting the payload.

    A model that invents an extra field has still answered the question, and
    `extra="forbid"` would throw away a good decision over a stray key.
    """
    model_config = ConfigDict(extra="ignore")

    reasoning: str = ""


# ---------------------------------------------------------------------------

class Understanding(_Decision):
    """What the student wants, and whether we can act on it yet."""

    intent: str = "answer"
    route: Route = "answer"
    normalized_query: str = ""
    is_followup: bool = False
    continues_topic: bool = False
    topic: str = ""
    needs_clarification: bool = False
    clarification_question: str = ""
    confidence: float = 0.5
    preferences: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {}
        route = _one_of(data.get("route"),
                        ("answer", "questions", "mark", "clarify", "chat"), "answer")
        needs = _as_bool(data.get("needs_clarification"))
        question = _as_str(data.get("clarification_question"))

        # A clarify route with no question to ask would render an empty
        # bubble. The model flagged ambiguity but could not say what was
        # ambiguous, which is not actionable — proceed instead.
        if needs and not question:
            needs = False
        if needs:
            route = "clarify"
        elif route == "clarify":
            # The reverse: routed to clarify without setting the flag.
            needs = bool(question)
            if not needs:
                route = "answer"

        prefs = data.get("preferences")
        return {
            "intent": _as_str(data.get("intent"), route),
            "route": route,
            "normalized_query": _as_str(data.get("normalized_query")),
            "is_followup": _as_bool(data.get("is_followup")),
            "continues_topic": _as_bool(data.get("continues_topic")),
            "topic": _as_str(data.get("topic")),
            "needs_clarification": needs,
            "clarification_question": question,
            "confidence": _as_float(data.get("confidence"), 0.5),
            "preferences": prefs if isinstance(prefs, dict) else {},
            "reasoning": _as_str(data.get("reasoning")),
        }


class RetrievalPlan(_Decision):
    """How to find the material — or whether to look at all."""

    should_retrieve: bool = True
    reuse_previous: bool = False
    search_query: str = ""
    keywords: list[str] = Field(default_factory=list)
    lesson_title_hint: str = ""
    metadata_filters: dict[str, Any] = Field(default_factory=dict)
    budget: int = 12
    use_doc_filter: bool = True
    use_conversation_context: bool = False

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {}
        filters = data.get("metadata_filters")
        return {
            "should_retrieve": _as_bool(data.get("should_retrieve"), True),
            "reuse_previous": _as_bool(data.get("reuse_previous")),
            "search_query": _as_str(data.get("search_query")),
            "keywords": _as_list(data.get("keywords")),
            "lesson_title_hint": _as_str(data.get("lesson_title_hint")),
            "metadata_filters": filters if isinstance(filters, dict) else {},
            "budget": _as_int(data.get("budget"), 12, 1, MAX_BUDGET),
            "use_doc_filter": _as_bool(data.get("use_doc_filter"), True),
            "use_conversation_context": _as_bool(data.get("use_conversation_context")),
            "reasoning": _as_str(data.get("reasoning")),
        }


class RetrievalVerdict(_Decision):
    """Is what we found enough, and if not, what next."""

    sufficient: bool = True
    confidence: float = 0.5
    missing_concepts: list[str] = Field(default_factory=list)
    next_action: NextAction = "proceed"
    rewritten_query: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {}
        action = _one_of(data.get("next_action"),
                         ("proceed", "rewrite", "widen", "give_up"), "proceed")
        rewritten = _as_str(data.get("rewritten_query"))

        # A rewrite instruction with no rewritten query would re-run the
        # identical search, spend a call, and get the identical result.
        if action == "rewrite" and not rewritten:
            action = "widen"

        return {
            "sufficient": _as_bool(data.get("sufficient"), True),
            "confidence": _as_float(data.get("confidence"), 0.5),
            "missing_concepts": _as_list(data.get("missing_concepts")),
            "next_action": action,
            "rewritten_query": rewritten,
            "reasoning": _as_str(data.get("reasoning")),
        }


class QuizPlan(_Decision):
    """What kind of practice set, and how much of it."""

    qtype: QType = "mcq"
    count: int = 5
    difficulty: Difficulty = "medium"
    bloom_level: str = "understand"
    topics: list[str] = Field(default_factory=list)
    include_explanations: bool = True

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {}
        return {
            # The prompt asks for `question_type`; the field is `qtype`
            # because that is what the database column is called. Both
            # spellings accepted rather than relying on the model using one.
            "qtype": _one_of(data.get("question_type") or data.get("qtype"),
                             ("mcq", "true_false", "short", "structured", "essay"),
                             "mcq"),
            "count": _as_int(data.get("count"), 5, 1, MAX_COUNT),
            "difficulty": _one_of(data.get("difficulty"),
                                  ("easy", "medium", "hard"), "medium"),
            "bloom_level": _as_str(data.get("bloom_level"), "understand"),
            "topics": _as_list(data.get("topics")),
            "include_explanations": _as_bool(data.get("include_explanations"), True),
            "reasoning": _as_str(data.get("reasoning")),
        }


class AnswerPlan(_Decision):
    """Style hints for a prose answer.

    Small, because ANSWER.md does the real work — this carries only what the
    CONVERSATION implies and the prompt cannot know.
    """

    style: str = ""
    include_citations: bool = True

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {}
        return {
            "style": _as_str(data.get("style")),
            "include_citations": _as_bool(data.get("include_citations"), True),
            "reasoning": _as_str(data.get("reasoning")),
        }
