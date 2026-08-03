"""
agent/state.py
==============

The LangGraph state schema — the working memory, as a TypedDict the graph
threads between nodes.

WHY A TypedDict AND NOT THE DATACLASS
-------------------------------------
LangGraph merges each node's returned dict into the state and passes the
result on. A TypedDict is what it expects, and it means a node returns ONLY
the keys it changed rather than a whole mutated object — so reading a node
tells you exactly what it writes.

REDUCERS
--------
Most fields overwrite: the newest retrieval plan replaces the old one. Three
do not, and they use `operator.add` so concurrent or repeated writes append
instead of clobbering:

    steps    the reasoning trace, appended by every node
    errors   accumulated, never replaced — a generation failure after a
             retrieval failure must not hide the first one
    tool_calls  a counter, summed

Without a reducer on `steps`, the last node to write would be the only one in
the trace, and the trace is the thing you read when an answer is wrong.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    # --- input, set once at invoke ---------------------------------------
    query: str
    user_id: str
    session_id: str
    doc_ids: list[str]
    submission: list[dict[str, Any]]

    # --- memory, loaded by the first node --------------------------------
    conversation: dict[str, Any]
    previous_retrieval: dict[str, Any]

    # --- decisions --------------------------------------------------------
    route: str
    understanding: dict[str, Any]
    retrieval_plan: dict[str, Any]
    quiz_plan: dict[str, Any]
    answer_plan: dict[str, Any]
    verdict: dict[str, Any]

    # --- retrieval working set -------------------------------------------
    search_query: str          # mutates across rewrites; the PLAN's copy does not
    budget: int
    lesson_title: str
    titles: list[str]
    chunks: list[dict[str, Any]]
    attempt: int
    reused_retrieval: bool

    # --- output -----------------------------------------------------------
    answer: str
    citations: list[dict[str, Any]]
    questions: list[dict[str, Any]]
    practice_set_id: str | None
    results: list[dict[str, Any]]
    total_marks: float
    total_max: float
    clarification: str
    reason: str | None

    # --- accumulated ------------------------------------------------------
    steps: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
    tool_calls: Annotated[int, operator.add]


def initial_state(*, query: str, user_id: str, session_id: str,
                  doc_ids: list[str] | None = None,
                  submission: list[dict] | None = None) -> AgentState:
    """Every accumulated field must start present and empty.

    LangGraph applies a reducer only to keys a node returns; a key absent from
    the initial state and then returned by a node is set, not reduced. Starting
    them empty means `operator.add` always has a left operand and the first
    node's steps are not silently dropped.
    """
    return AgentState(
        query=query, user_id=user_id, session_id=session_id,
        doc_ids=doc_ids or [], submission=submission or [],
        chunks=[], titles=[], questions=[], results=[], citations=[],
        answer="", clarification="", reason=None, route="",
        attempt=0, reused_retrieval=False, lesson_title="",
        steps=[], errors=[], tool_calls=0,
    )


def step(kind: str, name: str, ms: float = 0.0, **detail: Any) -> dict[str, Any]:
    """One trace entry. Never contains chunk text — chunks are copyrighted
    passages, and a trace that ships them to a browser is a copyright leak
    wearing an observability hat."""
    return {"kind": kind, "name": name, "ms": round(ms, 1), **detail}
