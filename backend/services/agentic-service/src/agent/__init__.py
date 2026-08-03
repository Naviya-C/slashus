"""The agent: a LangGraph StateGraph whose every branch is an LLM decision.

    agent/state.py      the graph state (TypedDict + reducers)
    agent/decisions.py  what the LLM may return (pydantic, coercing)
    agent/brain.py      the decisions themselves — one method, one prompt
    agent/nodes.py      nodes and edge routers
    agent/graph.py      the StateGraph wiring and the checkpointer

Nothing in agent/ touches a database, a gRPC channel, or Qdrant. Actions go
through tools/, which injects ownership from the authenticated session.

The heavy names are exported LAZILY (PEP 562). Importing `agent.state` or
`agent.nodes` should not drag in LangGraph, pydantic and tenacity — a
preflight script that only wants the state schema, or a test that only
exercises the edge routers, has no reason to need the whole stack installed.
"""

from agent.state import AgentState, initial_state, step

_LAZY = {
    "Brain": "agent.brain",
    "AgentRunner": "agent.graph",
    "build_agent": "agent.graph",
    "build_graph": "agent.graph",
    "Understanding": "agent.decisions",
    "RetrievalPlan": "agent.decisions",
    "RetrievalVerdict": "agent.decisions",
    "QuizPlan": "agent.decisions",
    "AnswerPlan": "agent.decisions",
}


def __getattr__(name: str):
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    return getattr(importlib.import_module(module), name)


__all__ = [
    "AgentState", "initial_state", "step",
    "Brain", "AgentRunner", "build_agent", "build_graph",
    "Understanding", "RetrievalPlan", "RetrievalVerdict", "QuizPlan", "AnswerPlan",
]
