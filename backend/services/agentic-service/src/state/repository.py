"""
src/state/repository.py
=======================

All Postgres access for sessions, messages, practice sets and answers.

Every method takes user_id and filters on it. Session and question ids appear
in URLs and in the browser, so a query scoped only by id would let any
authenticated caller read or mark another user's work. The gateway proved WHO
they are; it did not prove the row is theirs.

Pagination is keyset, never OFFSET — see the note at the bottom of schema.py.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.schema import (
    ChatMessage,
    ChatSession,
    PracticeAnswer,
    PracticeQuestion,
    PracticeSet,
)

logger = logging.getLogger(__name__)

_TITLE_MAX = 60


class Repository:
    def __init__(self, session_factory) -> None:
        self._sf = session_factory

    # --------------------------sessions-------------------------------- 

    def list_sessions(
        self, user_id: UUID, limit: int = 20, cursor: datetime | None = None
    ) -> dict[str, Any]:
        """Sidebar list, newest activity first.

        `cursor` is the last_message_at of the last row the client already
        has. Absent means the first page.
        """
        with self._sf() as db:
            stmt = (
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.last_message_at.desc())

                .limit(limit + 1)
            )
            if cursor is not None:
                stmt = stmt.where(ChatSession.last_message_at < cursor)

            rows = db.scalars(stmt).all()
            has_more = len(rows) > limit
            rows = rows[:limit]

            return {
                "sessions": [
                    {
                        "id": str(s.id),
                        "title": s.title,
                        "doc_ids": [str(d) for d in s.doc_ids],
                        "last_message_at": s.last_message_at.isoformat(),
                    }
                    for s in rows
                ],
                "next_cursor": rows[-1].last_message_at.isoformat() if has_more else None,
            }

    def get_or_create_session( 
        self, user_id: UUID, session_id: UUID | None, first_message: str,
        doc_ids: list[UUID] | None = None,
    ) -> ChatSession:
        with self._sf() as db:
            if session_id is not None:
                s = db.scalar(
                    select(ChatSession).where(
                        ChatSession.id == session_id, ChatSession.user_id == user_id
                    )
                )
                if s is not None:
                    return s

            s = ChatSession(
                user_id=user_id,
                title=first_message[:_TITLE_MAX],
                doc_ids=doc_ids or [],
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            return s

    # --------------------------messages-------------------------------- 

    def list_messages(
        self, user_id: UUID, session_id: UUID, limit: int = 30,
        cursor: datetime | None = None,
    ) -> dict[str, Any]:
        """One session's history, newest first, for scroll-back pagination."""
        with self._sf() as db:
            stmt = (
                select(ChatMessage)
                .where(
                    ChatMessage.session_id == session_id,
                    ChatMessage.user_id == user_id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(limit + 1)
            )
            if cursor is not None:
                stmt = stmt.where(ChatMessage.created_at < cursor)

            rows = db.scalars(stmt).all()
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
                        "practice_set_id": str(m.practice_set_id) if m.practice_set_id else None,
                        "created_at": m.created_at.isoformat(),
                    }

                    for m in reversed(rows)
                ],
                "next_cursor": rows[-1].created_at.isoformat() if has_more else None,
            }

    def add_turn(
        self, user_id: UUID, session_id: UUID, user_message: str,
        assistant_message: str, intent: str | None = None,
        citations: list | None = None, practice_set_id: UUID | None = None,
    ) -> None:
        with self._sf() as db:
            db.add(ChatMessage(
                session_id=session_id, user_id=user_id,
                role="user", content=user_message,
            ))
            db.add(ChatMessage(
                session_id=session_id, user_id=user_id,
                role="assistant", content=assistant_message,
                intent=intent, citations=citations,
                practice_set_id=practice_set_id,
            ))

            db.execute(
                ChatSession.__table__.update()
                .where(ChatSession.id == session_id)
                .values(last_message_at=datetime.now().astimezone())
            )
            db.commit()

    # ----------------------practice------------------------------------ 

    def save_practice_set(
        self, user_id: UUID, session_id: UUID, prompt: str,
        doc_ids: list, questions: list[dict],
    ) -> str:
        with self._sf() as db:
            ps = PracticeSet(
                user_id=user_id, session_id=session_id, prompt=prompt,
                doc_ids=[UUID(str(d)) for d in doc_ids],
            )
            db.add(ps)
            db.flush()   # assigns ps.id without ending the transaction

            for q in questions:
                db.add(PracticeQuestion(
                    practice_set_id=ps.id,
                    user_id=user_id,
                    position=q["position"],
                    qtype=q["qtype"],
                    question=q["question"],
                    options=q.get("options"),
                    correct_index=q.get("correct_index"),
                    explanation=q.get("explanation"),
                    model_answer=q.get("model_answer"),
                    rubric=q.get("rubric"),
                    sources=q.get("sources"),
                    max_marks=q.get("max_marks", 10),
                ))

            db.commit()
            logger.info("saved practice set %r (%s)", ps.id, type(ps.id).__name__)

            return ps.id

    def get_practice_set(self, set_id: UUID, user_id: UUID) -> dict | None:
        """A set with its questions and any answers — used to restore the
        right panel when a user reopens an old session."""
        with self._sf() as db:
            ps = db.scalar(
                select(PracticeSet)
                .where(PracticeSet.id == set_id, PracticeSet.user_id == user_id)
                .options(
                    selectinload(PracticeSet.questions).selectinload(PracticeQuestion.answer)
                )
            )
            if ps is None:
                return None

            return {
                "id": str(ps.id),
                "prompt": ps.prompt,
                "created_at": ps.created_at.isoformat(),
                "questions": [
                    {
                        "id": str(q.id),
                        "type": q.qtype,
                        "question": q.question,
                        "options": q.options or [],
                        # Sent for instant client-side MCQ feedback. See the
                        # note in contracts.Question about the trade.
                        "correct_index": q.correct_index,
                        "max_marks": q.max_marks,
                        "answer": self._answer_dict(q.answer),
                    }
                    for q in ps.questions
                ],
            }

    @staticmethod
    def _answer_dict(a: PracticeAnswer | None) -> dict | None:
        if a is None:
            return None
        return {
            "selected_index": a.selected_index,
            "answer_text": a.answer_text,
            "marks": float(a.marks) if a.marks is not None else None,
            "is_correct": a.is_correct,
            "feedback": a.feedback,
            "revealed_answer": a.revealed_answer,
        }

    # -------------------------marking--------------------------------- 

    def get_question(self, question_id: UUID, user_id: UUID) -> dict | None:
        with self._sf() as db:
            q = db.scalar(
                select(PracticeQuestion).where(
                    PracticeQuestion.id == question_id,
                    PracticeQuestion.user_id == user_id,
                )
            )
            if q is None:
                return None
            return {
                "id": q.id,
                "qtype": q.qtype,
                "question": q.question,
                "options": q.options or [],
                "correct_index": q.correct_index,
                "model_answer": q.model_answer,
                "rubric": q.rubric or [],
                "explanation": q.explanation,
                "max_marks": q.max_marks,
            }

    def get_question_sources(self, question_id: UUID) -> list[dict]:
        with self._sf() as db:
            q = db.get(PracticeQuestion, question_id)
            return (q.sources or []) if q else []

    def save_answer(
        self, question_id: UUID, user_id: UUID, selected_index: int | None,
        answer_text: str | None, result: dict,
    ) -> None:
        with self._sf() as db:
            existing = db.scalar(
                select(PracticeAnswer).where(PracticeAnswer.question_id == question_id)
            )
            
            a = existing or PracticeAnswer(question_id=question_id, user_id=user_id)

            a.selected_index = selected_index
            a.answer_text = answer_text
            a.marks = result.get("marks")
            a.is_correct = result.get("is_correct")
            a.feedback = result.get("feedback")
            a.revealed_answer = result.get("revealed_answer")
            a.marked_at = datetime.now().astimezone()

            if existing is None:
                db.add(a)
            db.commit()
