"""
The agent.

A real ReAct loop built on `langchain.agents.create_agent` tool schemas are
bound to the model via native function calling, and the model decides at each
iteration whether to call a tool, which one, with what arguments, or to answer.
Nothing here prescribes a path.


WHERE THE FOUR MEMORY TYPES ATTACH
----------------------------------
    WORKING     ``SummarizationMiddleware`` bounds the message window and
                summarises the overflow, before EVERY model call in the loop
                rather than once per user turn. Persisted by the checkpointer
                under thread_id.

    SEMANTIC    Recalled by vector search in ``MemoryRecallMiddleware`` and
                injected into the system prompt. 

    EPISODIC    Recalled as few-shot exemplars by the same middleware. Written
                only by consolidation, after the turn completes.

    PROCEDURAL  Loaded as behavioural rules and injected into the system
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
)
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from agentic_service.config.settings import AgentSettings
from agentic_service.memory.manager import MemoryManager
from agentic_service.observability.metrics import MEMORY_RECALL

log = structlog.get_logger(__name__)


class TutorState(AgentState):
    """Agent state plus this turn's recalled memory."""

    recalled: str
    recalled_turn_id: str


class MemoryRecallMiddleware(AgentMiddleware):
    """
    Injects semantic, episodic and procedural memory into the system prompt.
    """

    state_schema = TutorState

    def __init__(self, memory: MemoryManager, base_prompt: str) -> None:
        super().__init__()
        self._memory = memory
        self._base_prompt = base_prompt

    @staticmethod
    def _user_id(runtime: Any) -> str:
        """Identity from the run context, never from the model."""
        context = getattr(runtime, "context", None)
        if isinstance(context, dict) and context.get("user_id"):
            return str(context["user_id"])
        config = getattr(runtime, "config", None) or {}
        return str((config.get("configurable") or {}).get("user_id", ""))

    async def abefore_model(self, state: TutorState, runtime: Any) -> dict[str, Any] | None:
        # updates the agent state before each model call
        humans = [message for message in state["messages"] if message.type == "human"]
        latest = humans[-1] if humans else None
        query = str(latest.content) if latest is not None else ""
        """
        turn_id:
            - Number of human messages
            - Latest message ID, if available.
        """
        turn_id = f"{len(humans)}:{getattr(latest, 'id', '') or query[:80]}"
        if state.get("recalled_turn_id") == turn_id:
            """
            This prevents unnecessary Qdrant/PostgreSQL memory searches, reducing latency and cost.
            """
            return None

        started = time.perf_counter()
        recalled = await self._memory.recall(self._user_id(runtime), query) # The MemoryManager searches for relevant
        """
        This `MEMORY_RECALL` helps to find:
            - Performance bottleneck
            - Average recall latency
            - Slow memory searches
        """
        
        MEMORY_RECALL.observe(time.perf_counter() - started)

        rendered = recalled.render() # The raw memory lists are converted into prompt-ready text.
        log.info(
            "agent.memory_recalled",
            semantic=len(recalled.semantic),
            episodic=len(recalled.episodic),
            procedural=len(recalled.procedural),
            chars=len(rendered),
        )
        return {"recalled": rendered, "recalled_turn_id": turn_id}

    async def awrap_model_call(self, request: ModelRequest, handler: Any) -> Any:
        """
        Fold recalled memory into the system prompt for this call.
        This wraps the actual Qwen API call
        """
        recalled = ""
        state = getattr(request, "state", None)
        if isinstance(state, dict):
            recalled = state.get("recalled") or ""
        if recalled:
            request.system_prompt = f"{self._base_prompt}\n\n{recalled}"
        return await handler(request)


def build_agent(
    *,
    model: Any,
    tools: list,
    memory: MemoryManager,
    store: BaseStore,
    checkpointer: BaseCheckpointSaver | None,
    settings: AgentSettings,
    base_prompt: str,
    summarization_model: Any = None,
) -> Any: 
    """
    Compile the agent with memory and its termination guarantees.
    This function builds and returns the complete Slashus ReAct agent by connecting:
        Qwen model
        Slashus tools
        Memory middleware
        Conversation summarization
        Tool-call limits
        Checkpoint persistence
        Long-term store
    """
    middleware: list[AgentMiddleware] = [MemoryRecallMiddleware(memory, base_prompt)]

    if settings.summarization_enabled:
        middleware.append(
            SummarizationMiddleware(
                model=summarization_model or model,
                trigger=("tokens", settings.max_window_tokens),
                keep=("messages", settings.keep_recent_messages),
            )
        )

    middleware.append(ToolCallLimitMiddleware(thread_limit=settings.max_tool_calls))

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=base_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
        store=store,
        name="slashus-tutor",
    )
    log.info(
        "agent.compiled",
        tools=[t.name for t in tools],
        middleware=[type(m).__name__ for m in middleware],
    )
    return agent
