"""The agent: an LLM that reasons, and tools that execute.

    load_memory -> understand -> plan_retrieval -> retrieve -> evaluate
                -> (rewrite -> retrieve)*  -> generate -> save_memory

Every diamond in that flow is an LLM decision. Every box is deterministic
Python. See agent/graph.py.
"""

from agent.brain import Brain
from agent.decisions import (
    AnswerPlan,
    QuizPlan,
    RetrievalPlan,
    RetrievalVerdict,
    Understanding,
)
from agent.graph import AgentGraph, build_agent

__all__ = [
    "Brain", "AgentGraph", "build_agent",
    "Understanding", "RetrievalPlan", "RetrievalVerdict", "QuizPlan", "AnswerPlan",
]
