"""
Working memory: the bounded message window for the current thread.
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
    out = list(messages)

    while out and isinstance(out[0], ToolMessage):
        out.pop(0)

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
    if not messages:
        return []

    trimmed = trim_messages(
        messages,
        max_tokens=max_tokens,
        token_counter=token_counter,
        strategy="last",
        start_on="human",
        include_system=False,
        allow_partial=False,
    )

    trimmed = repair_boundaries(list(trimmed))
    if not trimmed:
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
    return [RemoveMessage(id=REMOVE_ALL_MESSAGES)]


__all__ = [
    "build_window",
    "clear_thread",
    "repair_boundaries",
    "summarise_overflow",
]
