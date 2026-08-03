"""
agent/graph.py
==============

The LangGraph StateGraph.

    START
      └─> load_memory
            └─> understand ──┬── clarify ──────────────> save_memory ─> END
                             ├── chat ──> small_talk ──> save_memory ─> END
                             └── retrieve
                                   └─> plan_retrieval ──┬── generate
                                                        ├── reuse ─┬─ generate
                                                        │          └─ search
                                                        ├── resolve_title ─> retrieve
                                                        └── search ─> retrieve
                                                                        │
                                     ┌──────── retry ─────────────┐     │
                                     │                            ▼     ▼
                                     └───────────────────────── evaluate
                                                                  │
                                            ┌── questions ─> plan_quiz ─> generate_questions ─┐
                                            ├── answer ────> plan_answer ─> generate_answer ──┤
                                            └── save ────────────────────────────────────────┤
                                                                                              ▼
                                                                                        save_memory ─> END

WHY THE CHECKPOINTER MATTERS HERE
---------------------------------
`thread_id` is the session id, so LangGraph persists state per conversation.
Three things follow:

  * A turn that dies mid-loop — rate limit on the third rewrite, container
    restart — resumes from the last completed node instead of re-running the
    search and the two decisions before it.
  * The retry loop's intermediate state survives, so `attempt` and the
    rewritten query are not lost to a transient failure.
  * Conversation state has a durable home that is not hand-rolled Redis
    plumbing.

Redis-backed when REDIS_URL is set. MemorySaver otherwise, which is correct
for one replica and quietly wrong for several — a follow-up landing on a
different container finds no thread.
"""

from __future__ import annotations

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.brain import Brain
from agent.nodes import (
    build_nodes,
    route_after_evaluate,
    route_after_plan,
    route_after_retrieve,
    route_after_reuse,
    route_after_understand,
    route_to_generator,
)
from agent.state import AgentState, initial_state
from core.config import settings

logger = logging.getLogger(__name__)


def _checkpointer():
    """Redis when available, in-memory otherwise.

    Degrades rather than fails: without a checkpointer the agent still answers,
    it just cannot resume a crashed turn. That is not worth taking chat down
    for, so a Redis problem logs and falls back.
    """
    if not settings.redis_url:
        logger.warning("REDIS_URL unset — LangGraph checkpoints are in-process "
                       "only, so a follow-up on another replica finds no thread")
        return MemorySaver()
    try:
        from langgraph.checkpoint.redis import RedisSaver
        saver = RedisSaver.from_conn_string(settings.redis_url)
        # from_conn_string returns a context manager in some versions and a
        # saver in others. Normalising here keeps the difference out of the
        # build path.
        saver = saver.__enter__() if hasattr(saver, "__enter__") else saver
        saver.setup()
        logger.info("LangGraph checkpointer: redis")
        return saver
    except Exception:
        logger.warning("redis checkpointer unavailable; using in-memory",
                       exc_info=True)
        return MemorySaver()


def build_graph(brain: Brain, tools, memory, checkpointer=None):
    nodes = build_nodes(brain, tools, memory)

    builder = StateGraph(AgentState)
    for name, fn in nodes.items():
        builder.add_node(name, fn)

    builder.add_edge(START, "load_memory")

    # Marking never goes through understanding: the student pressed Mark, not
    # Send. There is no intent to infer, and inferring one would add a call
    # and a failure mode to a path with no ambiguity. The entry point is
    # overridden at invoke time (see AgentRunner.mark).
    builder.add_conditional_edges(
        "load_memory",
        lambda s: "mark" if s.get("submission") else "understand",
        {"mark": "mark", "understand": "understand"},
    )

    builder.add_conditional_edges(
        "understand", route_after_understand,
        {"clarify": "save_memory", "chat": "small_talk", "retrieve": "plan_retrieval"},
    )
    builder.add_edge("small_talk", "save_memory")

    builder.add_conditional_edges(
        "plan_retrieval", route_after_plan,
        {"generate": "plan_answer", "reuse": "reuse_retrieval",
         "resolve_title": "resolve_lesson_title", "search": "retrieve"},
    )
    builder.add_conditional_edges(
        "reuse_retrieval", route_after_reuse,
        {"generate": "plan_answer", "search": "retrieve"},
    )
    builder.add_edge("resolve_lesson_title", "retrieve")

    builder.add_conditional_edges(
        "retrieve", route_after_retrieve,
        {"save": "save_memory", "evaluate": "evaluate"},
    )
    builder.add_conditional_edges(
        "evaluate", route_after_evaluate,
        {"retry": "retrieve", "generate": "_generate"},
    )

    # A pass-through so both the evaluate loop and the reuse path converge on
    # one place that chooses questions vs prose. Without it, that routing
    # table would be duplicated on two edges and drift.
    builder.add_node("_generate", lambda state: {})
    builder.add_conditional_edges(
        "_generate", route_to_generator,
        {"questions": "plan_quiz", "answer": "plan_answer", "save": "save_memory"},
    )

    builder.add_edge("plan_quiz", "generate_questions")
    builder.add_edge("generate_questions", "save_memory")
    builder.add_edge("plan_answer", "generate_answer")
    builder.add_edge("generate_answer", "save_memory")
    builder.add_edge("mark", "save_memory")
    builder.add_edge("save_memory", END)

    return builder.compile(checkpointer=checkpointer or _checkpointer())


class AgentRunner:
    """Thin wrapper over the compiled graph.

    Exists so api/server.py never touches LangGraph config dicts, and so the
    thread_id convention lives in one place — get it wrong and two students
    share a conversation.
    """

    def __init__(self, graph) -> None:
        self._graph = graph

    def run(self, *, query: str, user_id, session_id: str,
            doc_ids: list[str] | None = None,
            submission: list[dict] | None = None) -> dict:
        state = initial_state(
            query=query, user_id=str(user_id), session_id=session_id,
            doc_ids=doc_ids or [], submission=submission or [],
        )
        config = {
            "configurable": {
                # The checkpoint thread. Session id, NOT user id — a user has
                # many conversations and they must not share state.
                "thread_id": f"{user_id}:{session_id}",
            },
            # Hard stop on graph steps, independent of the tool budget. Guards
            # against a routing bug producing a cycle no decision can break.
            "recursion_limit": 40,
        }
        return self._graph.invoke(state, config=config)


def build_agent(*, vector_client, repo, llm, scratch, generator, marker,
                checkpointer=None) -> AgentRunner:
    """Composition root."""
    from memory import build_memory_store
    from tools import build_tools

    memory = build_memory_store(scratch, repo)
    tools = build_tools(vector_client, repo, generator, marker, memory)
    graph = build_graph(Brain(llm), tools, memory, checkpointer)
    return AgentRunner(graph)
