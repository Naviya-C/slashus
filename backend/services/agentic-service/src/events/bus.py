"""Event bus — the seam for the FUTURE event-driven / API-gateway architecture.

RIGHT NOW the orchestrator runs agents in-process, synchronously. But every
agent boundary also emits domain EVENTS through this bus. Today the only
subscriber is a logger (and tests). When you move to event-driven:

  - an API gateway publishes `UserQueryReceived` to a queue
  - each agent becomes a consumer of its trigger event and a publisher of its
    result event (RetrievalCompleted -> GenerationRequested -> ...)
  - the orchestrator becomes a saga/choreographer over these events

The InProcessEventBus below is the synchronous implementation used now. The
async/queue implementation is sketched in comments — swapping the bus binding
in the composition root is the only change; agents publish/subscribe the same
way. This keeps the system loosely coupled and migration-ready.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Event:
    type: str                         # e.g. "RetrievalCompleted"
    session_id: str
    payload: dict[str, Any] = field(default_factory=dict)


Handler = Callable[[Event], None]


class EventBus(Protocol):
    def publish(self, event: Event) -> None: ...
    def subscribe(self, event_type: str, handler: Handler) -> None: ...


class InProcessEventBus:
    """Synchronous, in-memory. Handlers run inline on publish."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = {}

    def publish(self, event: Event) -> None:
        logger.debug("event %s (session=%s)", event.type, event.session_id)
        for handler in self._subs.get(event.type, []):
            try:
                handler(event)
            except Exception:
                logger.exception("event handler failed for %s", event.type)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subs.setdefault(event_type, []).append(handler)


# ---------------------------------------------------------------------------
# FUTURE: async / distributed bus (event-driven architecture).
# Uncomment + implement when moving off in-process orchestration. Agents and
# the orchestrator use the SAME publish/subscribe interface, so only the
# binding in the composition root changes.
#
# class RedisStreamsEventBus:
#     """Distributed bus over Redis Streams (or Kafka/NATS/SQS)."""
#
#     def __init__(self, url: str) -> None:
#         import redis
#         self._r = redis.from_url(url)
#
#     def publish(self, event: Event) -> None:
#         self._r.xadd(f"events:{event.type}", {
#             "session_id": event.session_id,
#             "payload": json.dumps(event.payload),
#         })
#
#     def subscribe(self, event_type: str, handler: Handler) -> None:
#         # a consumer group worker reads the stream and dispatches to handler;
#         # runs in a separate process/worker, not inline.
#         ...
#
# Event names that would flow through the gateway:
#   UserQueryReceived -> IntentRouted -> RetrievalCompleted ->
#   GenerationCompleted -> EvaluationCompleted -> MarkingCompleted ->
#   ResponseReady
# ---------------------------------------------------------------------------


def build_event_bus() -> EventBus:
    # FUTURE: if settings.event_bus_url: return RedisStreamsEventBus(...)
    return InProcessEventBus()
