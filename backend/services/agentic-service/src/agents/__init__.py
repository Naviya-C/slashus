"""Importing this package registers every agent (their @register runs).

Add a new agent:
  1. create agents/<name>/ with agent.py (@register Agent subclass) + __init__.py
  2. add one import line below
Orchestrator and graph are untouched.
"""

from agents import generator, marker, retrieval  # noqa: F401  (import = register)
from agents.base import (
    Agent,
    AgentContext,
    Capability,
    build_registry,
    register,
    registered_names,
)

__all__ = [
    "Agent", "AgentContext", "Capability",
    "build_registry", "register", "registered_names",
]
