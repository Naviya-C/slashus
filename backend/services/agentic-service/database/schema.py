from __future__ import annotations

from datetime import datetime

import uuid
from sqlalchemy import BigInteger, DateTime, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True) # not migrated
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    assistant_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # jsonb default '{}'
    # NOTE: attribute is `meta`, column is "metadata" — SQLAlchemy reserves
    # `.metadata` on declarative classes, so the name must differ.
    meta: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=True
    )

    # timestamptz default now()
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    __table_args__ = (
        Index("conversation_turns_session_created_idx", "session_id", "created_at"),
    )