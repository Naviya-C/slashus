"""
Component health registry.

Components register here and report their own state. Liveness and readiness are
separated, because they answer different questions and conflating them causes
restart loops:

  LIVENESS  is the process itself wedged? Only a deadlock or a corrupt process
            should fail this. A brief Qdrant outage must NOT, or the
            orchestrator restarts a service whose only fault is a dependency
            being slow.

  READINESS is this instance able to serve right now, A model still loading,
            or a dead consumer thread, fails this -- traffic is routed away
            without the container being killed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum

import structlog

from agentic_service.observability.metrics import COMPONENT_UP

log = structlog.get_logger(__name__)


class ComponentState(StrEnum):
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass(slots=True)
class ComponentStatus:
    name: str
    state: ComponentState = ComponentState.STARTING
    detail: str = ""
    required: bool = True
    updated_at: float = field(default_factory=time.monotonic)


class HealthRegistry:
    def __init__(self) -> None:
        self._components: dict[str, ComponentStatus] = {}
        self._shutting_down = False

    def register(self, name: str, *, required: bool = True) -> None:
        self._components[name] = ComponentStatus(name=name, required=required)
        COMPONENT_UP.labels(component=name).set(0)

    def set(self, name: str, state: ComponentState, detail: str = "") -> None:
        status = self._components.get(name)
        if status is None:
            self.register(name)
            status = self._components[name]

        if status.state != state:
            log.info("health.state_changed", component=name, state=state.value, detail=detail)

        status.state = state
        status.detail = detail
        status.updated_at = time.monotonic()
        COMPONENT_UP.labels(component=name).set(1 if state is ComponentState.HEALTHY else 0)

    def begin_shutdown(self) -> None:
        """
        Fail readiness immediately, keep liveness green.

        Called on SIGTERM so the load balancer drains this instance while
        in-flight requests finish, instead of receiving new work right up to
        the moment the process exits.
        """
        self._shutting_down = True
        log.info("health.draining")

    @property
    def is_alive(self) -> bool:
        return not any(
            c.state is ComponentState.FAILED for c in self._components.values() if c.required
        )

    @property
    def is_ready(self) -> bool:
        if self._shutting_down:
            return False
        return all(
            c.state is ComponentState.HEALTHY for c in self._components.values() if c.required
        )

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {
            name: {
                "state": c.state.value,
                "detail": c.detail,
                "required": c.required,
                "age_seconds": round(time.monotonic() - c.updated_at, 1),
            }
            for name, c in self._components.items()
        }
