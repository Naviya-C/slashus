"""Self-registration and instantiation of agents.

Agents decorate themselves with @register; the orchestrator discovers them
through build_registry(). Adding an agent never requires editing the
orchestrator or graph.
"""

from __future__ import annotations

import inspect
import logging

from agents.base.agent import Agent

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[Agent]] = {}


def register(cls: type[Agent]) -> type[Agent]:
    if not getattr(cls, "name", ""):
        raise ValueError(f"{cls.__name__} must set a non-empty `name`")
    if cls.name in _REGISTRY:
        logger.warning("agent %r already registered; overwriting", cls.name)
    _REGISTRY[cls.name] = cls
    return cls


def build_registry(repo=None, **overrides: Agent) -> dict[str, Agent]:
    """Instantiate all registered agents.

    `repo` is passed only to agents whose __init__ accepts it — the generator
    and marker persist practice sets, the retriever does not. Inspecting the
    signature means adding a dependency to one agent does not force every
    other agent to accept and ignore it.

    `overrides` inject fakes by name, used by tests.
    """
    instances: dict[str, Agent] = {}
    for name, cls in _REGISTRY.items():
        if name in overrides:
            continue
        try:
            if repo is not None and "repo" in inspect.signature(cls.__init__).parameters:
                instances[name] = cls(repo=repo)
            else:
                instances[name] = cls()
        except Exception:
            # One agent failing to construct must not take down the whole
            # registry — the orchestrator reports missing_agent for it and
            # everything else still works.
            logger.exception("could not construct agent %r", name)
    instances.update(overrides)
    return instances


def registered_names() -> list[str]:
    return sorted(_REGISTRY)
