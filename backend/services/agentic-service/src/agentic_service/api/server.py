from __future__ import annotations

import hmac
import time
import uuid
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from agentic_service.config.settings import Settings
from agentic_service.observability.health import HealthRegistry

log = structlog.get_logger(__name__)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: UUID | None = None
    doc_ids: list[UUID] | None = Field(default=None, max_length=3)
    stream: bool = False


class MarkRequest(BaseModel):
    question_id: UUID
    selected_index: int | None = None
    answer_text: str | None = Field(default=None, max_length=20_000)


def _cursor(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        log.warning("api.malformed_cursor", cursor=value[:40])
        return None


def create_app(*, settings: Settings, container: Any, health: HealthRegistry) -> FastAPI:
    app = FastAPI(
        title=settings.service_name,
        version=settings.service_version,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    
    if settings.security.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.security.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["*"],
        )


    @app.middleware("http")
    async def correlate(request: Request, call_next: Any) -> Response:
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id, path=request.url.path)
        started = time.perf_counter()
        
        try:
            response = await call_next(request)
            
            response.headers["X-Correlation-Id"] = correlation_id
            log.info(
                "http.request",
                status=response.status_code,
                ms=round((time.perf_counter() - started) * 1000, 1),
            )
            return response
        finally:
                structlog.contextvars.unbind_contextvars("correlation_id", "path")

    async def current_user(
        x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
        x_gateway_secret: Annotated[str | None, Header(alias="X-Gateway-Secret")] = None,
    ) -> UUID:
        expected = settings.security.gateway_shared_secret
        
        if expected is not None and not hmac.compare_digest(
            x_gateway_secret or "", expected.get_secret_value()
        ):
            log.warning("api.gateway_secret_mismatch")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
        
        return x_user_id


    @app.post("/api/v1/chat", tags=["chat"])
    async def chat(
        body: ChatRequest,
        user_id: UUID = Depends(current_user)
    ) -> Any:
        session = await container.repository.get_or_create_session(
            user_id=user_id,
            session_id=body.session_id,
            first_message=body.message,
            doc_ids=body.doc_ids,
        )
        
        session_id = session["id"]
        doc_ids = list(session["doc_ids"])

        if body.stream:
            import json as _json

            async def events():
                async for event in container.runner.stream(
                    message=body.message,
                    user_id=user_id,
                    session_id=session_id,
                    doc_ids=doc_ids,
                ):
                    if event.get("type") == "turn_completed":
                        try:
                            await container.repository.add_turn(
                                user_id=user_id,
                                session_id=UUID(session_id),
                                user_message=body.message,
                                assistant_message=str(event.get("reply", "")),
                                intent="agent",
                                citations=event.get("citations") or [],
                            )
                        except Exception:
                            log.error(
                                "api.stream_turn_not_persisted",
                                session_id=session_id,
                                exc_info=True,
                            )
                    yield f"data: {_json.dumps(event)}\n\n"

            return StreamingResponse(events(), media_type="text/event-stream")

        result = await container.runner.run(
            message=body.message,
            user_id=user_id,
            session_id=session_id,
            doc_ids=doc_ids,
        )

        try:
            await container.repository.add_turn(
                user_id=user_id,
                session_id=UUID(session_id),
                user_message=body.message,
                assistant_message=result.reply,
                intent="agent",
                citations=result.citations,
            )
        except Exception:
            log.error("api.turn_not_persisted", session_id=session_id, exc_info=True)

        return {
            "session_id": session_id,
            "reply": result.reply,
            "tools_used": result.tool_calls,
            "iterations": result.iterations,
            "timed_out": result.timed_out,
            "citations": result.citations,
        }

    @app.get("/api/v1/practice/{set_id}", tags=["practice"])
    async def practice_set(
        set_id: UUID,
        user_id: UUID = Depends(current_user),
    ) -> dict[str, Any]:
        result = await container.repository.get_practice_set(set_id=set_id, user_id=user_id)
        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "practice set not found")
        return result

    @app.post("/api/v1/mark", tags=["practice"])
    async def mark(
        body: MarkRequest,
        user_id: UUID = Depends(current_user)
    ) -> dict[str, Any]:
        try:
            return await container.evaluator.evaluate_and_save(
                repository=container.repository,
                user_id=user_id,
                question_id=body.question_id,
                selected_index=body.selected_index,
                answer_text=body.answer_text,
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


    @app.get("/api/v1/memory", tags=["memory"])
    async def memory(
        query: str = "",
        user_id: UUID = Depends(current_user),
    ) -> dict[str, Any]:
        context = await container.memory.recall(str(user_id), query or "study")
        return {
            "semantic": [{"text": m.text, "payload": m.payload} for m in context.semantic],
            "episodic": [{"text": m.text} for m in context.episodic],
            "procedural": [
                {"instruction": r.instruction, "scope": r.scope, "version": r.version}
                for r in context.procedural
            ],
        }

    @app.delete("/api/v1/memory/{kind}", tags=["memory"])
    async def forget(
        kind: str,
        user_id: UUID = Depends(current_user),
    ) -> dict[str, Any]:
        if kind not in {"semantic", "episodic", "procedural"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown memory type {kind!r}")

        count = await container.memory.erase(str(user_id), kind)
        log.info("api.memory_erased", kind=kind, count=count)
        return {"erased": count, "kind": kind}


    @app.get("/api/v1/sessions", tags=["sessions"])
    async def sessions(
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
        cursor: str | None = None,
        user_id: UUID = Depends(current_user),
    ) -> dict[str, Any]:
        return await container.repository.list_sessions(
            user_id=user_id, limit=limit, cursor=_cursor(cursor)
        )

    @app.get("/api/v1/sessions/{session_id}", tags=["sessions"])
    async def session_messages(
        session_id: UUID,
        limit: Annotated[int, Query(ge=1, le=100)] = 30,
        cursor: str | None = None,
        user_id: UUID = Depends(current_user),
    ) -> dict[str, Any]:
        return await container.repository.list_messages(
            user_id=user_id, session_id=session_id, limit=limit, cursor=_cursor(cursor)
        )


    @app.get("/health/live", tags=["health"])
    async def liveness() -> JSONResponse:
        alive = health.is_alive
        return JSONResponse(
            status_code=200 if alive else 503,
            content={"status": "alive" if alive else "dead"},
        )

    @app.get("/health/ready", tags=["health"])
    async def readiness() -> JSONResponse:
        ready = health.is_ready
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ready" if ready else "not_ready",
                "components": health.snapshot(),
            },
        )

    if settings.observability.metrics_enabled:

        @app.get("/metrics", include_in_schema=False)
        async def metrics() -> Response:
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
