"""
SQLAlchemy ORM models
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ChatSession(TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    doc_ids: Mapped[list[uuid.UUID]] = mapped_column(JSONB, nullable=False, default=list)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sessions_user_recent", "user_id", "last_message_at"),
    )


class ChatMessage(TimestampMixin, Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    intent: Mapped[str | None] = mapped_column(String(32))
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    practice_set_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    session: Mapped[ChatSession] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
        Index("ix_messages_user", "user_id"),
    )


class PracticeSet(TimestampMixin, Base):
    __tablename__ = "practice_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    doc_ids: Mapped[list[uuid.UUID]] = mapped_column(JSONB, nullable=False, default=list)

    questions: Mapped[list[PracticeQuestion]] = relationship(
        back_populates="practice_set",
        cascade="all, delete-orphan",
        order_by="PracticeQuestion.position",
    )

    __table_args__ = (Index("ix_practice_sets_user_session", "user_id", "session_id"),)


class PracticeQuestion(TimestampMixin, Base):
    __tablename__ = "practice_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    practice_set_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practice_sets.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qtype: Mapped[str] = mapped_column(String(24), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str] | None] = mapped_column(JSONB)
    correct_index: Mapped[int | None] = mapped_column(Integer)
    explanation: Mapped[str | None] = mapped_column(Text)
    model_answer: Mapped[str | None] = mapped_column(Text)
    rubric: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    practice_set: Mapped[PracticeSet] = relationship(back_populates="questions")
    answer: Mapped[PracticeAnswer | None] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        UniqueConstraint("practice_set_id", "position", name="uq_question_position"),
        Index("ix_questions_user", "user_id"),
    )


class PracticeAnswer(TimestampMixin, Base):
    __tablename__ = "practice_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("practice_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    selected_index: Mapped[int | None] = mapped_column(Integer)
    answer_text: Mapped[str | None] = mapped_column(Text)
    marks: Mapped[float | None] = mapped_column(Numeric(6, 2))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    feedback: Mapped[str | None] = mapped_column(Text)
    revealed_answer: Mapped[str | None] = mapped_column(Text)
    rubric_results: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    question: Mapped[PracticeQuestion] = relationship(back_populates="answer")

    __table_args__ = (
        UniqueConstraint("question_id", name="uq_answer_per_question"),
        Index("ix_answers_user", "user_id"),
    )


class AgentMemory(TimestampMixin, Base):
    __tablename__ = "agent_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    searchable_text: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "kind", "content_hash", name="uq_agent_memory_content"),
        Index("ix_agent_memories_user_kind", "user_id", "kind", "active"),
    )
