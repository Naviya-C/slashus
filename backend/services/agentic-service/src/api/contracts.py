"""
src/api/contracts.py
====================

The wire format between this service and the frontend.

Every response carries `kind`, which tells the client WHERE to render:

    "message"   -> middle column, the conversation
    "questions" -> right panel, the practice set
    "marking"   -> right panel, updates the practice set in place

`reply` is always present and always renders in the chat column — so a
generation produces both a chat line ("Generated 5 questions.") and panel
content. That matches the screenshot: the conversation stays continuous while
structured work accumulates on the right.

Built as an explicit envelope rather than returning ctx.data raw, for two
reasons: the frontend stops depending on internal agent key names, and there
is exactly one place where correct answers can be stripped before they leave
the process.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Kind(str, Enum):
    MESSAGE = "message"
    QUESTIONS = "questions"
    MARKING = "marking"


class Reason(str, Enum):
    """Why a request could not be served. The frontend renders a different
    prompt for each — telling a user with no documents to "refresh" is useless,
    and telling a user with documents to "upload files" is wrong."""

    NO_DOCUMENTS = "no_documents"        # nothing in Qdrant for this user
    NO_RELEVANT_CHUNKS = "no_relevant"   # documents exist, none matched
    NOT_IN_SOURCE = "not_in_source"      # retrieved, but couldn't answer from it


@dataclass(slots=True)
class Option:
    """One MCQ choice.

    `index` is stored explicitly rather than implied by array position, so the
    frontend can shuffle options for display without breaking marking.
    """
    index: int
    text: str


@dataclass(slots=True)
class Question:
    """One question, in the shape the frontend renders directly.

    The client picks its widget from the data — no separate render hint, since
    two sources of truth eventually disagree:

        options non-empty  -> radio group
        options empty      -> textarea

    NOTE ON correct_index: it IS sent to the client, because you asked for
    instant MCQ marking without a round trip. That is a real trade — anyone
    can read it in DevTools. It is acceptable here because this is
    self-directed study with no grade attached; it would NOT be acceptable for
    a graded assessment, where marking must happen server-side. The written
    types never carry their model answer for the same reason, since those DO
    require a server call to mark.
    """
    id: str
    type: str                        # mcq | true_false | short | structured | essay
    question: str
    options: list[Option] = field(default_factory=list)
    correct_index: int | None = None
    explanation: str | None = None   # shown only after submission
    max_marks: int = 10
    source_pages: list[int] = field(default_factory=list)


@dataclass(slots=True)
class QuestionResult:
    """One question's outcome after marking."""
    question_id: str
    marks: float
    max_marks: int
    is_correct: bool | None          # None for written answers — they are graded, not binary
    feedback: str
    rubric_breakdown: list[dict[str, Any]] = field(default_factory=list)
    # Populated only when marks < 5. See MARK_WRITTEN.md on why.
    revealed_answer: str | None = None


@dataclass(slots=True)
class ChatResponse:
    session_id: str
    kind: Kind
    reply: str

    intent: str = ""
    # Present when kind == QUESTIONS.
    practice_set_id: str | None = None
    questions: list[Question] = field(default_factory=list)
    # Present when kind == MARKING.
    results: list[QuestionResult] = field(default_factory=list)
    total_marks: float | None = None
    total_max: float | None = None
    # Present when kind == MESSAGE and the answer was document-grounded.
    citations: list[dict[str, Any]] = field(default_factory=list)

    # Set when the request could not be served. The frontend switches on this
    # rather than string-matching the reply text.
    reason: Reason | None = None

    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["reason"] = self.reason.value if self.reason else None
        # Drop empty keys so the payload stays readable in a network inspector.
        return {k: v for k, v in d.items() if v not in (None, [], "")} | {
            "session_id": self.session_id,
            "kind": self.kind.value,
            "reply": self.reply,
        }


# ---------------------------------------------------------------------------
# Blocked-request replies
# ---------------------------------------------------------------------------
# Written out as constants rather than inline, so the wording is reviewable in
# one place and translatable later.

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
}


def blocked(session_id: str, reason: Reason) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        kind=Kind.MESSAGE,
        reply=BLOCKED_REPLIES[reason],
        reason=reason,
    )
