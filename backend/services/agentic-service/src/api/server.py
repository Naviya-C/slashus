"""
src/api/server.py
=================

    POST /chat              question, generation, or conversation
    POST /mark              grade a submission
    GET  /sessions          sidebar list (keyset paginated)
    GET  /sessions/{id}     one session's messages (keyset paginated)
    GET  /practice/{id}     restore a practice set with its answers
    GET  /health

Identity comes from X-User-Id, injected by the api-gateway from a verified
token. This service is only reachable through the gateway.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from agents import AgentContext
from agents.marker import MarkerAgent
from api.contracts import ChatResponse, Kind, Question, QuestionResult, Reason, blocked

from orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

api = FastAPI(title="Slashus Agentic Service")

_orch: Orchestrator | None = None
_repo = None


def get_orchestrator() -> Orchestrator:
    global _orch
    if _orch is None:
        _orch = Orchestrator()
    return _orch


def get_repo():
    global _repo
    if _repo is None:
        from database.session import SessionLocal
        from state.repository import Repository
        _repo = Repository(SessionLocal)
    return _repo


def current_user(x_user_id: UUID = Header(..., alias="X-User-Id")) -> UUID:
    return x_user_id


def _cursor(value: str | None) -> datetime | None:
    """Parse an ISO cursor, treating anything malformed as absent.

    Rejecting a bad cursor with a 400 would break a client mid-scroll for no
    benefit; returning page one is recoverable.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        logger.warning("ignoring malformed cursor %r", value)
        return None


# ------------------------schemas------------------------------------------ 

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: UUID | None = None
    doc_ids: list[UUID] = Field(default_factory=list, max_length=3)


class SubmissionItem(BaseModel):
    question_id: UUID
    selected_index: int | None = None
    answer_text: str | None = None


class MarkRequest(BaseModel):
    session_id: UUID
    submission: list[SubmissionItem] = Field(..., min_length=1)


# --------------------------chat------------------------------------------- 

@api.post("/api/v1/chat")
def chat(req: ChatRequest, user_id: UUID = Depends(current_user)):
    repo = get_repo()

    session = repo.get_or_create_session(
        user_id=user_id,
        session_id=req.session_id,
        first_message=req.message,
        doc_ids=req.doc_ids,
    )

    result = get_orchestrator().run(
        req.message,
        user_id=user_id,
        session_id=str(session.id),
        doc_ids=[str(d) for d in req.doc_ids],
    )

    reason = result.get("reason")
    if reason:
        resp = blocked(str(session.id), Reason(reason))
        repo.add_turn(
            user_id, session.id, req.message, resp.reply, intent=result.get("intent")
        )
        return resp.to_dict()

    data = result.get("data", {})
    questions = data.get("questions", [])

    if questions:
        resp = ChatResponse(
            session_id=str(session.id),
            kind=Kind.QUESTIONS,
            reply=result.get("reply", f"Generated {len(questions)} questions."),
            intent=result.get("intent", ""),
            practice_set_id=data.get("practice_set_id"),
            questions=[
                Question(
                    id=q.get("id", ""),
                    type=q["qtype"],
                    question=q["question"],
                    options=q.get("options", []),
                    correct_index=q.get("correct_index"),
                    explanation=q.get("explanation"),
                    max_marks=q.get("max_marks", 10),
                    source_pages=q.get("source_pages", []),
                )
                for q in questions
            ],
        )
    else:
        resp = ChatResponse(
            session_id=str(session.id),
            kind=Kind.MESSAGE,
            reply=result.get("reply", ""),
            intent=result.get("intent", ""),
            citations=data.get("citations", []),
        )

    repo.add_turn(
        user_id, session.id, req.message, resp.reply,
        intent=resp.intent,
        citations=resp.citations or None,
        practice_set_id=UUID(str(resp.practice_set_id)) if resp.practice_set_id else None,
    )
    return resp.to_dict()


# ---------------------------mark------------------------------------------ 

@api.post("/api/v1/mark")
def mark(req: MarkRequest, user_id: UUID = Depends(current_user)):
    """Grade a submission.

    A separate endpoint rather than a /chat intent: the client already knows
    this is a marking action because the user pressed Mark, not Send. Routing
    it through intent classification would risk misreading a submission as
    conversation, and there is no ambiguity to resolve.
    """
    ctx = AgentContext(
        query="mark",
        user_id=user_id,
        session_id=str(req.session_id),
        data={"submission": [s.model_dump() for s in req.submission]},
    )
    MarkerAgent(repo=get_repo()).run(ctx)

    if ctx.errors:
        raise HTTPException(400, "nothing to mark")

    results = ctx.get("results", [])
    return ChatResponse(
        session_id=str(req.session_id),
        kind=Kind.MARKING,
        reply=f"Graded: {ctx.get('total_marks')}/{ctx.get('total_max')}.",
        intent="mark",
        results=[QuestionResult(**r) for r in results],
        total_marks=ctx.get("total_marks"),
        total_max=ctx.get("total_max"),
    ).to_dict()


# -------------------------sessions---------------------------------------- 

@api.get("/api/v1/sessions")
def sessions(
    user_id: UUID = Depends(current_user),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
):
    return get_repo().list_sessions(user_id, limit=limit, cursor=_cursor(cursor))


@api.get("/api/v1/sessions/{session_id}")
def session_messages(
    session_id: UUID,
    user_id: UUID = Depends(current_user),
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = None,
):
    return get_repo().list_messages(
        user_id, session_id, limit=limit, cursor=_cursor(cursor)
    )


@api.get("/api/v1/practice/{set_id}")
def practice_set(set_id: UUID, user_id: UUID = Depends(current_user)):
    """Restores the right panel — questions plus any answers already given,
    so reopening a session shows the student where they got to."""
    data = get_repo().get_practice_set(set_id, user_id)
    if data is None:
        raise HTTPException(404, "practice set not found")
    return data


@api.get("/health")
def health():
    """Liveness only — does not touch Qdrant, Postgres, or the LLM.

    A readiness probe that calls dependencies turns a brief outage into a
    container restart loop.
    """
    return {"status": "ok"}
