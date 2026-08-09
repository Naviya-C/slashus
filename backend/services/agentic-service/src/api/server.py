"""
    POST /api/v1/chat              the agent — explain, generate, clarify
    POST /api/v1/mark              grade a submission
    GET  /api/v1/sessions          sidebar list (keyset paginated)
    GET  /api/v1/sessions/{id}     one session's messages (keyset paginated)
    GET  /api/v1/sessions/{id}/memory   what the agent remembers  [NEW]
    GET  /api/v1/practice/{id}     restore a practice set with its answers
    GET  /health

Identity comes from X-User-Id, injected by the api-gateway from a verified
token. This service is only reachable through the gateway.

WHAT CHANGED FOR THE FRONTEND
-----------------------------
Every /chat and /mark response now carries three render flags that are always
present, never stripped:

    mode                    "normal" | "question_generation" | "marking"
                            | "clarification" | "blocked"
    is_question_generation  bool — open the practice panel
    render_target           "chat" | "practice_panel"
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from api.contracts import (
    ChatResponse,
    Question,
    QuestionResult,
    Reason,
    blocked,
)
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

api = FastAPI(title="Slashus Agentic Service")

_agent = None
_repo = None
_memory = None


def get_repo():
    global _repo
    if _repo is None:
        from database.session import SessionLocal
        from state.repository import Repository
        _repo = Repository(SessionLocal)
    return _repo


def get_agent():
    """Built once, lazily.

    Lazily because constructing it opens a gRPC channel and reads config, and
    doing that at import time makes the module unimportable in a test or a
    preflight script that has no embedding-service.
    """
    global _agent, _memory
    if _agent is None:
        from agent import build_agent
        from core.llm import QwenClient
        from memory import build_memory_store
        from services import GenerationService, MarkingService
        from state.scratch import Scratch
        from vectorstore import build_vector_client

        repo = get_repo()
        llm = QwenClient()
        scratch = Scratch(_redis())
        _memory = build_memory_store(scratch, repo)
        _agent = build_agent(
            vector_client=build_vector_client(),
            repo=repo,
            llm=llm,
            scratch=scratch,
            generator=GenerationService(llm, repo),
            marker=MarkingService(llm, repo),
        )
    return _agent


def _redis():
    if not settings.redis_url:
        logger.warning("REDIS_URL unset — agent memory is per-process only")
        return None
    try:
        import redis
        return redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        logger.warning("redis unavailable; agent memory is per-process only",
                       exc_info=True)
        return None


def current_user(x_user_id: UUID = Header(..., alias="X-User-Id")) -> UUID:
    return x_user_id


def _cursor(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        logger.warning("ignoring malformed cursor %r", value)
        return None


# --------------------------schemas----------------------------------------

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


# ----------------------------chat-----------------------------------------

@api.post("/api/v1/chat")
def chat(req: ChatRequest, user_id: UUID = Depends(current_user)):
    repo = get_repo()

    session = repo.get_or_create_session(
        user_id=user_id, session_id=req.session_id,
        first_message=req.message, doc_ids=req.doc_ids,
    )
    session_id = str(session.id)

    state = get_agent().run(
        query=req.message, user_id=user_id, session_id=session_id,
        doc_ids=[str(d) for d in req.doc_ids],
    )

    resp = _shape(state, session_id)

    repo.add_turn(
        user_id, session.id, req.message, resp.reply,
        intent=resp.intent,
        citations=resp.citations or None,
        practice_set_id=UUID(str(resp.practice_set_id)) if resp.practice_set_id else None,
    )
    return resp.to_dict()


def _shape(state: dict, session_id: str) -> ChatResponse:
    trace = state.get("steps", []) if settings.dev_mode else []
    errors = state.get("errors", [])

    if state.get("clarification"):
        return ChatResponse.for_clarification(
            session_id, state["clarification"], intent="clarify",
            trace=trace, errors=errors)

    reason = state.get("reason")
    if reason and not state.get("questions") and not state.get("answer"):
        resp = blocked(session_id, Reason(reason))
        resp.trace = trace
        resp.errors = errors
        return resp

    if state.get("questions"):
        plan = state.get("quiz_plan", {})
        return ChatResponse.for_questions(
            session_id,
            reply=f"Generated {len(state['questions'])} "
                  f"{plan.get('difficulty', '')} questions.".replace("  ", " "),
            intent=state.get("route", ""),
            practice_set_id=state.get("practice_set_id"),
            questions=[
                Question(
                    id=q.get("id", ""), type=q["qtype"], question=q["question"],
                    options=q.get("options", []),
                    correct_index=q.get("correct_index"),
                    explanation=q.get("explanation"),
                    max_marks=q.get("max_marks", 10),
                    source_pages=q.get("source_pages", []),
                    difficulty=plan.get("difficulty", "medium"),
                    bloom_level=plan.get("bloom_level", ""),
                )
                for q in state["questions"]
            ],
            trace=trace, errors=errors,
        )

    return ChatResponse.for_message(
        session_id, reply=state.get("answer", ""),
        intent=state.get("route", ""),
        citations=state.get("citations", []),
        reason=Reason(reason) if reason == "not_in_source" else None,
        trace=trace, errors=errors,
    )


# ----------------------------mark-----------------------------------------

@api.post("/api/v1/mark")
def mark(req: MarkRequest, user_id: UUID = Depends(current_user)):
    state = get_agent().run(
        query="mark", user_id=user_id, session_id=str(req.session_id),
        submission=[s.model_dump() for s in req.submission],
    )

    results = state.get("results", [])
    if not results:
        raise HTTPException(400, "nothing to mark")

    total = round(sum(r["marks"] for r in results), 1)
    out_of = sum(r["max_marks"] for r in results)

    return ChatResponse.for_marking(
        str(req.session_id),
        reply=f"Graded: {total}/{out_of}.",
        intent="mark",
        results=[QuestionResult(**r) for r in results],
        total_marks=total, total_max=out_of,
        trace=state.get("steps", []) if settings.dev_mode else [],
    ).to_dict()


# --------------------------sessions---------------------------------------

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


@api.get("/api/v1/sessions/{session_id}/memory")
def session_memory(session_id: UUID, user_id: UUID = Depends(current_user)):
    get_agent()   # ensures _memory is built
    loaded = _memory.load(user_id, str(session_id))
    return {
        "session_id": str(session_id),
        "conversation": {
            "summary": loaded.conversation.summary,
            "active_topic": loaded.conversation.active_topic,
            "preferences": loaded.conversation.preferences,
            "turn_count": loaded.conversation.turn_count,
        },
        "retrieval": {
            "description": loaded.retrieval.describe(),
            "query": loaded.retrieval.query,
            "keywords": loaded.retrieval.keywords,
            "lesson_titles": loaded.retrieval.lesson_titles,
            "chunk_count": len(loaded.retrieval.chunks),
        },
    }


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
