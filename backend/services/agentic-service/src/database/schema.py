"""
database/schema.py
==================

STORAGE DECISION: everything in Postgres. No MongoDB, no second store.

You asked whether question sessions need a different database because they
have a different shape (MCQs vs essays vs answers). They don't — that is
exactly what JSONB is for. Adding a document store would mean another
container on an 8 GB VM that is already tight, a second connection pool, a
second backup story, and cross-store joins in application code every time you
render a session list mixing chat and practice.

What actually differs is the ACCESS PATTERN, not the storage engine:

    chat turns       append-only, read newest-first, never updated
    practice sets    written once, then UPDATED repeatedly as the student
                     answers and marks

That difference is handled by separate tables, below — not separate databases.

Redis is used for exactly one thing (see preflight.py): caching "does this
user have any chunks in Qdrant", which would otherwise be a network round trip
on every single message. Session lists are NOT cached; they change on every
turn and Postgres serves them from an index in under a millisecond.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Sessions — one row per conversation thread (the "02 / SESSIONS" sidebar)
# ---------------------------------------------------------------------------

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Derived from the first user message, truncated. Denormalized on purpose:
    # rendering the sidebar would otherwise need a correlated subquery per row
    # to find each session's first message.
    title: Mapped[str] = mapped_column(String(120), nullable=False, server_default="New chat")

    # Which documents this session is scoped to. Empty array = all of the
    # user's documents. Stored so reopening a session restores the same
    # retrieval scope the user had when they created it — otherwise answers
    # silently change meaning between visits.
    doc_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Sort key for the sidebar. Separate from updated_at because a title edit
    # should not push a session to the top of the list.
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    practice_sets: Mapped[list["PracticeSet"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # The sidebar query: this user's sessions, newest activity first.
        # Also the cursor index — keyset pagination seeks straight into it.
        Index("ix_sessions_user_last_msg", "user_id", last_message_at.desc()),
    )


# ---------------------------------------------------------------------------
# Chat turns — the middle column
# ---------------------------------------------------------------------------

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    # Denormalized from the session. Costs 16 bytes per row and buys an
    # ownership check that does not need a join — which matters because EVERY
    # read of this table must be user-scoped.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Assistant turns only: the classified intent, and citations
    # ([{page, title, source}]). Citations are metadata about the answer, not
    # the answer — keeping them out of `content` means the UI can render or
    # hide them without parsing prose.
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Set when this turn produced questions, so the frontend knows to open the
    # practice panel when the user scrolls back to it.
    practice_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("practice_sets.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_message_role"),
        # Loading a session's history, newest first, for keyset pagination.
        Index("ix_messages_session_created", "session_id", created_at.desc()),
    )


# ---------------------------------------------------------------------------
# Practice sets — the right panel
# ---------------------------------------------------------------------------

class PracticeSet(Base):
    __tablename__ = "practice_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # The request that produced this set, kept so "give me more" can generate
    # in the same style without re-deriving it from conversation history.
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    doc_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["ChatSession"] = relationship(back_populates="practice_sets")
    questions: Mapped[list["PracticeQuestion"]] = relationship(
        back_populates="practice_set",
        cascade="all, delete-orphan",
        order_by="PracticeQuestion.position",
    )

    __table_args__ = (
        Index("ix_practice_sets_user_created", "user_id", created_at.desc()),
    )


class PracticeQuestion(Base):
    """One question. Shape varies by type; JSONB absorbs the variance.

    THE CORRECT ANSWER LIVES HERE AND ONLY HERE. It is never serialized into a
    generation response — see contracts.py. If it ships to the browser with
    the question, the practice set is decoration.
    """

    __tablename__ = "practice_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    practice_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("practice_sets.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    position: Mapped[int] = mapped_column(Integer, nullable=False)
    qtype: Mapped[str] = mapped_column(String(16), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # MCQ / true_false: [{"index": 0, "text": "..."}]. Empty for written types.
    # `index` is stored explicitly rather than implied by array position, so
    # the frontend can shuffle options without breaking marking.
    options: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # MCQ / true_false: the winning option index, as an int.
    correct_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Written types: the model answer, used both to mark and to show the
    # student when they score below the threshold.
    model_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Shown to the student AFTER they submit. MCQ only — written answers get
    # feedback generated at marking time against the rubric.
    #
    # There was no column for this: the generator produced it, the repository
    # silently dropped it, and get_question dug for it in rubric[0], which is
    # None for MCQs. Every MCQ fell back to "Correct."/"That's not right." and
    # taught the student nothing.
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Marking guidance for written answers: the points a full answer must hit.
    # Generated alongside the question, so the marker is not re-deriving the
    # rubric from the chunks every time someone submits.
    rubric: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Where in the source this came from: [{"page": 24, "chunk_id": "..."}].
    # Lets marking re-fetch exactly the right passages instead of running a
    # fresh retrieval that may surface different text than the question was
    # written from.
    sources: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")

    practice_set: Mapped["PracticeSet"] = relationship(back_populates="questions")
    answer: Mapped["PracticeAnswer | None"] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        CheckConstraint(
            "qtype IN ('mcq', 'true_false', 'short', 'structured', 'essay')",
            name="ck_question_type",
        ),
        # An MCQ without a correct answer is unmarkable, and a written question
        # with a correct_index is a generation bug. Enforce at the boundary
        # rather than discovering it at marking time.
        CheckConstraint(
            "(qtype IN ('mcq','true_false') AND correct_index IS NOT NULL)"
            " OR (qtype NOT IN ('mcq','true_false') AND correct_index IS NULL)",
            name="ck_question_answer_shape",
        ),
        Index("ix_questions_set_position", "practice_set_id", "position"),
    )


class PracticeAnswer(Base):
    """A student's response and its mark.

    Separate from the question so that "answered but not yet marked" is a real
    state — which it has to be, because you want instant MCQ marking AND the
    ability to come back and mark later.
    """

    __tablename__ = "practice_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # UNIQUE: one answer per question. Re-answering updates in place rather
    # than accumulating rows nothing knows how to choose between.
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("practice_questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Exactly one is set, depending on question type.
    selected_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # NULL until marked. This is what makes deferred marking work.
    marks: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Populated only when marks < the reveal threshold — showing the model
    # answer to someone who already got it right teaches nothing.
    revealed_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    question: Mapped["PracticeQuestion"] = relationship(back_populates="answer")

    __table_args__ = (
        Index("ix_answers_user", "user_id"),
    )


# ---------------------------------------------------------------------------
# PAGINATION: keyset, not OFFSET
# ---------------------------------------------------------------------------
# For the sidebar and for scrolling back through a session, use a cursor on the
# sort column rather than OFFSET:
#
#     SELECT * FROM chat_sessions
#     WHERE user_id = :uid AND last_message_at < :cursor
#     ORDER BY last_message_at DESC
#     LIMIT 20;
#
# OFFSET 200 makes Postgres walk and discard 200 rows every time; the index on
# (user_id, last_message_at DESC) lets a cursor seek straight to the position.
# It also cannot skip or duplicate rows when new messages arrive mid-scroll,
# which OFFSET does — and that is exactly the situation here, since the list
# reorders every time the user sends a message.
#
# The cursor is the last row's last_message_at. Return it as `next_cursor`;
# null means the end.
