"""Deterministic plan: budget scales with question count + complexity."""

from __future__ import annotations

from core.config import settings
from agents.retrieval.schemas import Plan, Understanding


def make_plan(u: Understanding) -> Plan:
    base = {"simple": 5, "moderate": 8, "complex": 12}.get(u.complexity, 8)
    budget = min(base * max(1, u.question_count), settings.max_chunk_budget)
    return Plan(
        chunk_budget=budget, 
        metadata_filters=dict(u.metadata),
        enable_reranking=settings.enable_reranking
        )
