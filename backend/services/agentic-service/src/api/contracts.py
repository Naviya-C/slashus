"""
src/api/contracts.py
====================

The wire format between this service and the frontend.

RENDER FLAGS
------------
`kind` says WHERE to render:

    "message"        middle column, the conversation
    "questions"      right panel, the practice set
    "marking"        right panel, updates the practice set in place
    "clarification"  middle column, but the agent is asking, not answering

`kind` alone required the frontend to know that "questions" and only
"questions" opens the practice panel — a string comparison repeated at every
call site, and one that breaks silently the day a fifth kind is added. So the
answer is also carried explicitly:

    is_question_generation   bool   the practice panel should open
    render_target            enum   "chat" | "practice_panel"
    mode                     enum   what the agent actually did

Three fields for one decision is redundant on purpose. `is_question_generation`
is the boolean to branch on; `render_target` is the field to switch layout on
without enumerating kinds; `mode` is what to log and show in a debug view. All
three are derived from one place (`ChatResponse.for_*`), so they cannot
disagree.

`mode` is the one to read if only one is read: it distinguishes
`question_generation` from `normal` even when a future kind renders in the
same place.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Kind(str, Enum):
    MESSAGE = "message"
    QUESTIONS = "questions"
    MARKING = "marking"
    CLARIFICATION = "clarification"


class Mode(str, Enum):
    """What the agent did. The flag to branch on in the frontend."""
    NORMAL = "normal"                              # explanation, summary, chat
    QUESTION_GENERATION = "question_generation"    # a practice set was created
    MARKING = "marking"                            # answers were graded
    CLARIFICATION = "clarification"                # the agent asked back
    BLOCKED = "blocked"                            # nothing could be produced


class RenderTarget(str, Enum):
    CHAT = "chat"
    PRACTICE_PANEL = "practice_panel"


class Reason(str, Enum):
    NO_DOCUMENTS = "no_documents"
    NO_RELEVANT_CHUNKS = "no_relevant"
    NOT_IN_SOURCE = "not_in_source"
    NEEDS_CLARIFICATION = "needs_clarification"


@dataclass(slots=True)
class Option:
    index: int
    text: str


@dataclass(slots=True)
class Question:
    id: str
    type: str                        # mcq | true_false | short | structured | essay
    question: str
    options: list[Option] = field(default_factory=list)
    correct_index: int | None = None
    explanation: str | None = None   # shown only after submission
    max_marks: int = 10
    source_pages: list[int] = field(default_factory=list)
    difficulty: str = "medium"
    bloom_level: str = ""


@dataclass(slots=True)
class QuestionResult:
    question_id: str
    marks: float
    max_marks: int
    is_correct: bool | None          # None for written — graded, not binary
    feedback: str
    rubric_breakdown: list[dict[str, Any]] = field(default_factory=list)
    revealed_answer: str | None = None


@dataclass(slots=True)
class ChatResponse:
    session_id: str
    kind: Kind
    reply: str

    # --- render flags -------------------------------------------------
    mode: Mode = Mode.NORMAL
    is_question_generation: bool = False
    render_target: RenderTarget = RenderTarget.CHAT

    # --- payload ------------------------------------------------------
    intent: str = ""
    practice_set_id: str | None = None
    questions: list[Question] = field(default_factory=list)
    results: list[QuestionResult] = field(default_factory=list)
    total_marks: float | None = None
    total_max: float | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    reason: Reason | None = None

    # --- observability -------------------------------------------------
    trace: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------

    @classmethod
    def for_questions(cls, session_id: str, **kwargs) -> ChatResponse:
        return cls(session_id=session_id, kind=Kind.QUESTIONS,
                   mode=Mode.QUESTION_GENERATION, is_question_generation=True,
                   render_target=RenderTarget.PRACTICE_PANEL, **kwargs)

    @classmethod
    def for_marking(cls, session_id: str, **kwargs) -> ChatResponse:
        return cls(session_id=session_id, kind=Kind.MARKING, mode=Mode.MARKING,
                   render_target=RenderTarget.PRACTICE_PANEL, **kwargs)

    @classmethod
    def for_message(cls, session_id: str, **kwargs) -> ChatResponse:
        return cls(session_id=session_id, kind=Kind.MESSAGE, mode=Mode.NORMAL,
                   render_target=RenderTarget.CHAT, **kwargs)

    @classmethod
    def for_clarification(cls, session_id: str, question: str,
                          **kwargs) -> ChatResponse:
        return cls(session_id=session_id, kind=Kind.CLARIFICATION,
                   mode=Mode.CLARIFICATION, render_target=RenderTarget.CHAT,
                   reply=question, reason=Reason.NEEDS_CLARIFICATION, **kwargs)

    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["mode"] = self.mode.value
        d["render_target"] = self.render_target.value
        d["reason"] = self.reason.value if self.reason else None
        
        return {k: v for k, v in d.items() if v not in (None, [], "")} | {
            "session_id": self.session_id,
            "kind": self.kind.value,
            "mode": self.mode.value,
            "is_question_generation": self.is_question_generation,
            "render_target": self.render_target.value,
            "reply": self.reply,
        }


# ---------------------------------------------------------------------------

BLOCKED_REPLIES: dict[Reason, str] = {
    Reason.NO_DOCUMENTS: (
        "You haven't uploaded any documents yet. Upload a PDF from the panel "
        "on the left, and I'll be able to answer questions about it."
    ),
    Reason.NO_RELEVANT_CHUNKS: (
        "I couldn't find anything about that in your documents. If you "
        "uploaded a file recently it may still be processing — wait a moment "
        "and try again. If it still doesn't work, delete the document and "
        "upload it again."
    ),
    Reason.NOT_IN_SOURCE: (
        "I found related material, but it doesn't cover this specific "
        "question. Try rephrasing, or check whether the right document is "
        "selected."
    ),
    Reason.NEEDS_CLARIFICATION: "Could you tell me a bit more about what you need?",
}


def blocked(session_id: str, reason: Reason) -> ChatResponse:
    return ChatResponse(
        session_id=session_id, kind=Kind.MESSAGE, mode=Mode.BLOCKED,
        render_target=RenderTarget.CHAT,
        reply=BLOCKED_REPLIES[reason], reason=reason,
    )
