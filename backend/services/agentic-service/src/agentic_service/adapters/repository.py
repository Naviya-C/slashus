"""Postgres access for sessions, messages, practice sets and answers.

Every method takes ``user_id`` and filters on it. Session and question ids
appear in URLs and in the browser, so a query scoped only by id would let any
authenticated caller read or mark another user's work. The gateway proved WHO
they are; it did not prove the row is theirs.

WHAT CHANGED
------------
* ASYNC. v1 used the blocking driver from sync endpoints, so every query held a
  threadpool worker for its full duration.
* ONE TRANSACTION PER UNIT OF WORK. ``add_turn`` in v1 opened a session, added
  two messages and ran a separate UPDATE, but ``save_answer`` did a SELECT then
  an INSERT in a pattern two concurrent submissions could race past. Ownership
  is verified inside the same transaction as the write.
* NO ORM OBJECTS ESCAPE. v1 returned a live ``ChatSession`` from inside a
  closed session scope; touching a lazy attribute afterwards raised
  ``DetachedInstanceError``. Plain dicts cross the boundary now.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from agentic_service.adapters.models_db import (
    ChatMessage,
    ChatSession,
    PracticeAnswer,
    PracticeQuestion,
    PracticeSet,
    utcnow,
)

log = structlog.get_logger(__name__)

TITLE_MAX = 60


class RepositoryError(RuntimeError):
    pass


class SqlChatRepository:
    """Adapter for :class:`agentic_service.ports.ChatRepository`."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    # -- sessions ---------------------------------------------------------

    async def get_or_create_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID | None,
        first_message: str,
        doc_ids: Sequence[UUID] | None = None,
    ) -> dict[str, Any]:
        async with self._sf() as db, db.begin():
            if session_id is not None:
                existing = await db.scalar(
                    select(ChatSession).where(
                        ChatSession.id == session_id, ChatSession.user_id == user_id
                    )
                )
                if existing is not None:
                    if doc_ids is not None:
                        existing.doc_ids = [str(d) for d in doc_ids]
                        await db.flush()
                    return self._session_dict(existing)

            created = ChatSession(
                # Honour a client-supplied id only after confirming it is not
                # already owned by someone else -- the lookup above did that.
                id=session_id or None,
                user_id=user_id,
                title=first_message[:TITLE_MAX],
                doc_ids=[str(d) for d in (doc_ids or ())],
            )
            if created.id is None:
                del created.id
            db.add(created)
            await db.flush()
            return self._session_dict(created)

    async def list_sessions(
        self, *, user_id: UUID, limit: int = 20, cursor: datetime | None = None
    ) -> dict[str, Any]:
        """Keyset pagination, newest activity first.

        ``cursor`` is the ``last_message_at`` of the last row the client has.
        Offset pagination would skip or repeat rows whenever a session's
        activity timestamp changes between pages, which for a chat sidebar is
        constantly.
        """
        async with self._sf() as db:
            stmt = (
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.last_message_at.desc(), ChatSession.id.desc())
                .limit(limit + 1)
            )
            if cursor is not None:
                stmt = stmt.where(ChatSession.last_message_at < cursor)

            rows = list(await db.scalars(stmt))
            has_more = len(rows) > limit
            rows = rows[:limit]

            return {
                "sessions": [self._session_dict(s) for s in rows],
                "next_cursor": rows[-1].last_message_at.isoformat() if has_more and rows else None,
            }

    @staticmethod
    def _session_dict(s: ChatSession) -> dict[str, Any]:
        return {
            "id": str(s.id),
            "title": s.title,
            "doc_ids": [str(d) for d in (s.doc_ids or [])],
            "last_message_at": s.last_message_at.isoformat(),
        }

    # -- messages ---------------------------------------------------------

    async def list_messages(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        limit: int = 30,
        cursor: datetime | None = None,
    ) -> dict[str, Any]:
        async with self._sf() as db:
            stmt = (
                select(ChatMessage)
                .where(
                    ChatMessage.session_id == session_id,
                    ChatMessage.user_id == user_id,
                )
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                .limit(limit + 1)
            )
            if cursor is not None:
                stmt = stmt.where(ChatMessage.created_at < cursor)

            rows = list(await db.scalars(stmt))
            has_more = len(rows) > limit
            rows = rows[:limit]

            return {
                "messages": [
                    {
                        "id": str(m.id),
                        "role": m.role,
                        "content": m.content,
                        "intent": m.intent,
                        "citations": m.citations or [],
                        "practice_set_id": (str(m.practice_set_id) if m.practice_set_id else None),
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in reversed(rows)
                ],
                "next_cursor": rows[-1].created_at.isoformat() if has_more and rows else None,
            }

    async def add_turn(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        assistant_message: str,
        intent: str | None = None,
        citations: list[dict[str, Any]] | None = None,
        practice_set_id: UUID | None = None,
    ) -> None:
        """Both messages and the session bump in ONE transaction.

        Splitting them lets a crash leave a user message with no reply, or a
        session whose ``last_message_at`` disagrees with its newest message.
        """
        async with self._sf() as db, db.begin():
            owned = await db.scalar(
                select(func.count())
                .select_from(ChatSession)
                .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            )
            if not owned:
                raise RepositoryError("session does not exist or is not owned by this user")

            now = utcnow()
            db.add(
                ChatMessage(
                    session_id=session_id,
                    user_id=user_id,
                    role="user",
                    content=user_message,
                    created_at=now,
                )
            )
            db.add(
                ChatMessage(
                    session_id=session_id,
                    user_id=user_id,
                    role="assistant",
                    content=assistant_message,
                    intent=intent,
                    citations=citations,
                    practice_set_id=practice_set_id,
                    created_at=now,
                )
            )
            await db.execute(
                update(ChatSession).where(ChatSession.id == session_id).values(last_message_at=now)
            )

    # -- practice ---------------------------------------------------------

    async def save_practice_set(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        prompt: str,
        doc_ids: Sequence[UUID],
        questions: list[dict[str, Any]],
    ) -> UUID:
        async with self._sf() as db, db.begin():
            owned = await db.scalar(
                select(func.count())
                .select_from(ChatSession)
                .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            )
            if not owned:
                raise RepositoryError("session does not exist or is not owned by this user")
            practice_set = PracticeSet(
                user_id=user_id,
                session_id=session_id,
                prompt=prompt,
                doc_ids=[str(d) for d in doc_ids],
            )
            db.add(practice_set)
            await db.flush()

            for position, q in enumerate(questions, start=1):
                db.add(
                    PracticeQuestion(
                        practice_set_id=practice_set.id,
                        user_id=user_id,
                        position=q.get("position", position),
                        qtype=q["qtype"],
                        question=q["question"],
                        options=q.get("options"),
                        correct_index=q.get("correct_index"),
                        explanation=q.get("explanation"),
                        model_answer=q.get("model_answer"),
                        rubric=q.get("rubric"),
                        sources=q.get("sources"),
                        max_marks=q.get("max_marks", 10),
                    )
                )
            await db.flush()
            set_id = practice_set.id

        log.info("repository.practice_set_saved", set_id=str(set_id), count=len(questions))
        return set_id

    async def get_practice_set(self, *, set_id: UUID, user_id: UUID) -> dict[str, Any] | None:
        async with self._sf() as db:
            practice_set = await db.scalar(
                select(PracticeSet)
                .where(PracticeSet.id == set_id, PracticeSet.user_id == user_id)
                .options(selectinload(PracticeSet.questions).selectinload(PracticeQuestion.answer))
            )
            if practice_set is None:
                return None

            return {
                "id": str(practice_set.id),
                "prompt": practice_set.prompt,
                "created_at": practice_set.created_at.isoformat(),
                "questions": [
                    {
                        "id": str(q.id),
                        "position": q.position,
                        "type": q.qtype,
                        "question": q.question,
                        "options": q.options or [],
                        "correct_index": q.correct_index if q.answer is not None else None,
                        "max_marks": q.max_marks,
                        "answer": self._answer_dict(q.answer),
                    }
                    for q in practice_set.questions
                ],
            }

    @staticmethod
    def _answer_dict(a: PracticeAnswer | None) -> dict[str, Any] | None:
        if a is None:
            return None
        return {
            "selected_index": a.selected_index,
            "answer_text": a.answer_text,
            "marks": float(a.marks) if a.marks is not None else None,
            "is_correct": a.is_correct,
            "feedback": a.feedback,
            "revealed_answer": a.revealed_answer,
            "rubric_results": a.rubric_results or [],
        }

    # -- marking ----------------------------------------------------------

    async def get_question(self, *, question_id: UUID, user_id: UUID) -> dict[str, Any] | None:
        async with self._sf() as db:
            q = await db.scalar(
                select(PracticeQuestion).where(
                    PracticeQuestion.id == question_id,
                    PracticeQuestion.user_id == user_id,
                )
            )
            if q is None:
                return None
            return {
                "id": str(q.id),
                "qtype": q.qtype,
                "question": q.question,
                "options": q.options or [],
                "correct_index": q.correct_index,
                "model_answer": q.model_answer,
                "rubric": q.rubric or [],
                "explanation": q.explanation,
                "max_marks": q.max_marks,
                "sources": q.sources or [],
            }

    async def save_answer(
        self,
        *,
        question_id: UUID,
        user_id: UUID,
        selected_index: int | None,
        answer_text: str | None,
        result: dict[str, Any],
    ) -> None:
        """Upsert one answer, inside the ownership check's transaction."""
        async with self._sf() as db, db.begin():
            owned = await db.scalar(
                select(func.count())
                .select_from(PracticeQuestion)
                .where(
                    PracticeQuestion.id == question_id,
                    PracticeQuestion.user_id == user_id,
                )
            )
            if not owned:
                raise RepositoryError("question does not exist or is not owned by this user")

            values = {
                "question_id": question_id,
                "user_id": user_id,
                "selected_index": selected_index,
                "answer_text": answer_text,
                "marks": result.get("marks"),
                "is_correct": result.get("is_correct"),
                "feedback": result.get("feedback"),
                "revealed_answer": result.get("revealed_answer"),
                "rubric_results": result.get("rubric_results") or [],
                "marked_at": utcnow(),
            }
            statement = pg_insert(PracticeAnswer).values(**values)
            await db.execute(
                statement.on_conflict_do_update(
                    constraint="uq_answer_per_question",
                    set_={key: value for key, value in values.items() if key != "question_id"},
                )
            )

    # -- health -----------------------------------------------------------

    async def healthy(self) -> bool:
        try:
            async with self._sf() as db:
                await db.execute(select(1))
            return True
        except SQLAlchemyError:
            log.warning("repository.ping_failed", exc_info=True)
            return False
