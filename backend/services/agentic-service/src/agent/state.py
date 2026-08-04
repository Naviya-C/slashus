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
    search_query: str         
    budget: int
    lesson_title: str
    title_confidence: float
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
    
    return AgentState(
        query=query, user_id=user_id, session_id=session_id,
        doc_ids=doc_ids or [], submission=submission or [],
        chunks=[], titles=[], questions=[], results=[], citations=[],
        answer="", clarification="", reason=None, route="",
        attempt=0, reused_retrieval=False, lesson_title="",
        steps=[], errors=[], tool_calls=0,
    )


def step(kind: str, name: str, ms: float = 0.0, **detail: Any) -> dict[str, Any]:
    return {"kind": kind, "name": name, "ms": round(ms, 1), **detail}
