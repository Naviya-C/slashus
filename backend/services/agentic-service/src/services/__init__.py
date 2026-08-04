"""Deterministic services the tools call.

These are not agents and they make no decisions. Generation renders a template
the agent chose and validates what comes back; marking compares against stored
answers and rubrics. Both were agents in the previous design, which meant the
decision of WHETHER to run them lived inside them — exactly the coupling the
rebase removes.
"""

from services.generation import GenerationService
from services.marking import MarkingService

__all__ = ["GenerationService", "MarkingService"]
