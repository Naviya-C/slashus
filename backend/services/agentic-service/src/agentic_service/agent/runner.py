"""Runs one turn of the agent.

Three responsibilities the agent graph itself should not carry:

  * A HARD TIMEOUT. A real agent chooses its own path, so nothing in the loop
    guarantees termination in bounded wall-clock time -- ``recursion_limit``
    bounds the number of steps, not how long they take. A model that calls a
    slow tool ten times stays inside the recursion limit and still holds the
    connection for minutes.

  * BACKGROUND CONSOLIDATION. Episodic and procedural memory are written after
    the response is sent, so the student never waits for them. This is the
    whole reason consolidation is not a node in the graph.

  * OBSERVABILITY of what the model actually chose. In a hardcoded pipeline the
    tool sequence is a constant; here it is the primary thing worth logging,
    because it is the only record of what the agent decided to do.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any
from uuid import UUID, uuid4

import structlog
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agentic_service.config.settings import AgentSettings
from agentic_service.memory.manager import MemoryManager
from agentic_service.observability.metrics import (
    CONSOLIDATIONS,
    LLM_TOKENS,
    LOOP_ITERATIONS,
    TURN_DURATION,
    TURN_OUTCOMES,
)

log = structlog.get_logger(__name__)


class TurnResult:
    __slots__ = (
        "citations",
        "iterations",
        "messages",
        "reply",
        "timed_out",
        "tokens",
        "tool_calls",
    )

    def __init__(
        self,
        *,
        reply: str,
        tool_calls: list[str],
        iterations: int,
        tokens: int,
        timed_out: bool = False,
        messages: list | None = None,
        citations: list[dict[str, Any]] | None = None,
    ) -> None:
        self.reply = reply
        self.tool_calls = tool_calls
        self.iterations = iterations
        self.tokens = tokens
        self.timed_out = timed_out
        self.messages = messages or []
        self.citations = citations or []


class TurnRunner:
    def __init__(
        self,
        *,
        agent: Any,
        memory: MemoryManager,
        settings: AgentSettings,
        cache: Any = None,
        consolidation_enabled: bool = True,
    ) -> None:
        self._agent = agent
        self._memory = memory
        self._cfg = settings
        self._cache = cache
        self._consolidate = consolidation_enabled
        # Held so shutdown can await them; a fire-and-forget task that is never
        # referenced can be garbage-collected mid-flight.
        self._background: set[asyncio.Task] = set()

    def _config(self, *, user_id: UUID, session_id: str, doc_ids: list[str]) -> dict:
        return {
            "configurable": {
                "thread_id": f"{user_id}:{session_id}",
                # Identity travels in config, never as a tool argument, so a
                # prompt injection inside a retrieved chunk has no slot in
                # which to name a different user.
                "user_id": str(user_id),
                "doc_ids": doc_ids,
                "turn_id": str(uuid4()),
            },
            "recursion_limit": self._cfg.recursion_limit,
        }

    async def run(
        self,
        *,
        message: str,
        user_id: UUID,
        session_id: str,
        doc_ids: list[str] | None = None,
    ) -> TurnResult:
        docs = doc_ids or []
        config = self._config(user_id=user_id, session_id=session_id, doc_ids=docs)
        started = time.perf_counter()

        # Whether this thread already has turns decides how an ambiguous
        # message is read: "explain more" opening a fresh session is a normal
        # question, but mid-conversation it is a follow-up whose answer depends
        # entirely on what came before -- never cacheable.
        has_history = await self._has_history(config)

        if self._cache is not None:
            hit = await self._cache.lookup(
                message=message,
                user_id=str(user_id),
                doc_ids=docs,
                has_history=has_history,
            )
            if hit is not None:
                TURN_OUTCOMES.labels(outcome="cache_hit").inc()
                TURN_DURATION.observe(time.perf_counter() - started)
                return TurnResult(
                    reply=hit.answer,
                    tool_calls=hit.tools_used,
                    iterations=0,
                    tokens=0,
                )

        try:
            state = await asyncio.wait_for(
                self._agent.ainvoke({"messages": [HumanMessage(content=message)]}, config),
                timeout=self._cfg.turn_timeout_seconds,
            )
        except TimeoutError:
            TURN_OUTCOMES.labels(outcome="timeout").inc()
            log.error("turn.timeout", limit=self._cfg.turn_timeout_seconds)
            return TurnResult(
                reply=(
                    "That took longer than expected to work through. Please try "
                    "asking it in a more specific way."
                ),
                tool_calls=[],
                iterations=0,
                tokens=0,
                timed_out=True,
            )
        except Exception:
            TURN_OUTCOMES.labels(outcome="error").inc()
            log.error("turn.failed", exc_info=True)
            raise

        result = self._summarise(state)
        await self._finish(
            message=message,
            user_id=str(user_id),
            docs=docs,
            has_history=has_history,
            started=started,
            result=result,
        )
        return result

    async def _finish(
        self,
        *,
        message: str,
        user_id: str,
        docs: list[str],
        has_history: bool,
        started: float,
        result: TurnResult,
    ) -> None:
        elapsed = time.perf_counter() - started
        TURN_DURATION.observe(elapsed)
        LOOP_ITERATIONS.observe(result.iterations)
        TURN_OUTCOMES.labels(outcome="ok").inc()

        log.info(
            "turn.completed",
            seconds=round(elapsed, 2),
            # The record of what the agent actually decided to do.
            tools=result.tool_calls,
            iterations=result.iterations,
            tokens=result.tokens,
        )

        if self._cache is not None:
            await self._cache.store(
                message=message,
                answer=result.reply,
                user_id=user_id,
                doc_ids=docs,
                tools_used=result.tool_calls,
                has_history=has_history,
                timed_out=result.timed_out,
            )

        if self._consolidate:
            self._schedule_consolidation(user_id, result)

    async def _has_history(self, config: dict) -> bool:
        """Does this thread already contain turns?"""
        try:
            state = await self._agent.aget_state(config)
            return bool((state.values or {}).get("messages"))
        except Exception:
            return False

    async def stream(
        self,
        *,
        message: str,
        user_id: UUID,
        session_id: str,
        doc_ids: list[str] | None = None,
    ):
        """Stream the turn as it happens.

        A real agent loop can spend twenty seconds on tool calls before the
        first token of prose. Emitting tool events as they occur is the
        difference between "thinking..." and a blank screen.
        """
        docs = doc_ids or []
        config = self._config(user_id=user_id, session_id=session_id, doc_ids=docs)
        started = time.perf_counter()
        has_history = await self._has_history(config)
        yield {"type": "turn_started", "session_id": session_id}

        if self._cache is not None:
            hit = await self._cache.lookup(
                message=message, user_id=str(user_id), doc_ids=docs, has_history=has_history
            )
            if hit is not None:
                yield {"type": "token", "text": hit.answer}
                yield {
                    "type": "turn_completed",
                    "session_id": session_id,
                    "reply": hit.answer,
                    "tools_used": hit.tools_used,
                    "iterations": 0,
                    "citations": [],
                }
                return

        try:
            async with asyncio.timeout(self._cfg.turn_timeout_seconds):
                async for mode, chunk in self._agent.astream(
                    {"messages": [HumanMessage(content=message)]},
                    config,
                    stream_mode=["updates", "messages"],
                ):
                    if mode == "messages":
                        token, _meta = chunk
                        if getattr(token, "content", "") and not getattr(token, "tool_calls", None):
                            yield {"type": "token", "text": token.content}
                    elif mode == "updates":
                        for _node, patch in (chunk or {}).items():
                            for msg in (patch or {}).get("messages", []) or []:
                                if isinstance(msg, AIMessage) and msg.tool_calls:
                                    for call in msg.tool_calls:
                                        yield {"type": "tool_started", "tool": call["name"]}
                                elif isinstance(msg, ToolMessage):
                                    yield {"type": "tool_completed", "tool": msg.name}
        except TimeoutError:
            yield {"type": "error", "code": "timeout", "message": "The turn timed out."}
            return
        except Exception as exc:
            log.error("turn.stream_failed", exc_info=True)
            yield {"type": "error", "code": "agent_error", "message": str(exc)[:200]}
            return

        state = await self._agent.aget_state(config)
        result = self._summarise(state.values or {})
        await self._finish(
            message=message,
            user_id=str(user_id),
            docs=docs,
            has_history=has_history,
            started=started,
            result=result,
        )
        yield {
            "type": "turn_completed",
            "session_id": session_id,
            "reply": result.reply,
            "tools_used": result.tool_calls,
            "iterations": result.iterations,
            "citations": result.citations,
        }

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _summarise(state: dict) -> TurnResult:
        all_messages = state.get("messages", [])
        start = max(
            (
                index
                for index, message in enumerate(all_messages)
                if isinstance(message, HumanMessage)
            ),
            default=0,
        )
        messages = all_messages[start:]
        tools: list[str] = []
        iterations = 0
        tokens = 0

        for msg in messages:
            if isinstance(msg, AIMessage):
                iterations += 1
                for call in msg.tool_calls or []:
                    tools.append(call["name"])
                if usage := getattr(msg, "usage_metadata", None):
                    tokens += usage.get("total_tokens", 0) or 0
                    LLM_TOKENS.labels(kind="prompt").inc(usage.get("input_tokens", 0) or 0)
                    LLM_TOKENS.labels(kind="completion").inc(usage.get("output_tokens", 0) or 0)

        reply = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                reply = str(msg.content)
                break

        registry: dict[str, dict[str, Any]] = {}
        for msg in messages:
            if not isinstance(msg, ToolMessage) or msg.name != "search_documents":
                continue
            try:
                payload = json.loads(str(msg.content))
            except (TypeError, json.JSONDecodeError):
                continue
            for passage in payload.get("passages", []):
                citation = str(passage.get("citation", ""))
                if citation:
                    registry[citation] = {
                        key: passage.get(key)
                        for key in (
                            "citation",
                            "chunk_id",
                            "doc_id",
                            "lesson_title",
                            "page",
                            "source",
                        )
                    }
        referenced = set(re.findall(r"\[(C-[A-F0-9]{10})\]", reply))
        invalid = referenced - set(registry)
        for citation in invalid:
            reply = reply.replace(f"[{citation}]", "")
        citations = [registry[key] for key in registry if key in referenced]

        return TurnResult(
            reply=reply,
            tool_calls=tools,
            iterations=iterations,
            tokens=tokens,
            messages=messages,
            citations=citations,
        )

    def _schedule_consolidation(self, user_id: str, result: TurnResult) -> None:
        conversation = [
            {"role": m.type, "content": str(m.content)}
            for m in result.messages
            if isinstance(m, HumanMessage | AIMessage) and m.content
        ]
        if len(conversation) < 2:
            return

        async def work() -> None:
            try:
                await self._memory.consolidate(
                    user_id, conversation=conversation, tools_used=result.tool_calls
                )
                CONSOLIDATIONS.labels(outcome="ok").inc()
            except Exception:
                CONSOLIDATIONS.labels(outcome="failed").inc()
                log.warning("consolidation.failed", exc_info=True)

        task = asyncio.create_task(work())
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def drain(self, grace_period_seconds: float = 10.0) -> None:
        """Await outstanding consolidations during shutdown."""
        if not self._background:
            return
        log.info("turn_runner.draining", pending=len(self._background))
        await asyncio.wait(set(self._background), timeout=grace_period_seconds)
