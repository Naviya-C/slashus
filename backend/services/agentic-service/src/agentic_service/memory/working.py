"""Working memory: the bounded message window for the current thread.

WHY THIS IS NOT JUST "THE MESSAGE LIST"
---------------------------------------
A real tool-calling agent generates a lot of messages per turn: every tool call
and every tool result is a message, and they all persist in thread state. Left
alone, a twenty-turn tutoring session carries hundreds of messages -- including
the full text of every retrieved Sinhala chunk -- into EVERY subsequent model
call. Cost and latency grow quadratically over a session, and the model's
attention is spent on stale retrievals rather than the current question.

Trimming runs as a ``pre_model_hook``, so it applies before every model call
inside the ReAct loop, not merely once per user turn.

Two invariants the trimmer must not break, because violating either produces a
hard API error rather than a degraded answer:

  1. The window must not begin with an orphaned ToolMessage. A ToolMessage
     whose matching AIMessage tool_call was trimmed away is a protocol error.
  2. An AIMessage carrying tool_calls must keep its ToolMessages. Trimming
     between them leaves the model waiting for results that never arrive.
"""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langgraph.graph.message import REMOVE_ALL_MESSAGES

log = structlog.get_logger(__name__)


def _has_tool_calls(message: AnyMessage) -> bool:
    return isinstance(message, AIMessage) and bool(message.tool_calls)


def repair_boundaries(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Drop leading orphaned tool results and trailing dangling tool calls."""
    out = list(messages)

    # Leading ToolMessages whose AIMessage was trimmed away.
    while out and isinstance(out[0], ToolMessage):
        out.pop(0)

    # A trailing AIMessage with unanswered tool_calls: the results were cut, so
    # the request must go too or the provider rejects the whole exchange.
    if out and _has_tool_calls(out[-1]):
        out.pop()

    return out


def build_window(
    messages: list[AnyMessage],
    *,
    max_tokens: int,
    token_counter: Any,
    system: SystemMessage | None = None,
) -> list[AnyMessage]:
    """Return the messages that should be sent to the model."""
    if not messages:
        return []

    trimmed = trim_messages(
        messages,
        max_tokens=max_tokens,
        token_counter=token_counter,
        strategy="last",
        # Keeps AIMessage/ToolMessage pairs together rather than splitting a
        # tool call from its result.
        start_on="human",
        include_system=False,
        allow_partial=False,
    )

    trimmed = repair_boundaries(list(trimmed))
    if not trimmed:
        # Everything was trimmed -- keep the final human turn so the model has
        # something to answer.
        trimmed = [m for m in messages if not isinstance(m, ToolMessage)][-1:]

    if system is not None:
        return [system, *trimmed]
    return trimmed


def summarise_overflow(
    messages: list[AnyMessage], keep_last: int
) -> tuple[list[AnyMessage], list[AnyMessage]]:
    """Split into (to_summarise, to_keep_verbatim)."""
    if len(messages) <= keep_last:
        return [], messages
    return messages[:-keep_last], messages[-keep_last:]


def clear_thread(messages: list[AnyMessage]) -> list[Any]:
    """Wipe thread state. Used when a session is explicitly reset."""
    return [RemoveMessage(id=REMOVE_ALL_MESSAGES)]


__all__ = [
    "build_window",
    "clear_thread",
    "repair_boundaries",
    "summarise_overflow",
]
