from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from agent.state import AgentState, step
from core.config import settings
from memory.retrieval import RetrievalSnapshot

logger = logging.getLogger(__name__)


def build_nodes(brain, tools, memory):
    """Bind dependencies and return {node_name: callable}."""

    def _call(state: AgentState, name: str, args: dict) -> Any:
        result = tools.execute(name, args,
                               user_id=UUID(state["user_id"]),
                               session_id=state["session_id"])
        patch = {
            "tool_calls": 1,
            "steps": [step("tool", name, result.ms, outcome=result.summary())],
        }
        return result, patch

    # ==================================================================

    def load_memory(state: AgentState) -> dict:
        started = time.perf_counter()
        loaded = memory.load(UUID(state["user_id"]), state["session_id"])
        return {
            "conversation": {
                "summary": loaded.conversation.summary,
                "active_topic": loaded.conversation.active_topic,
                "preferences": loaded.conversation.preferences,
                "recent_turns": loaded.conversation.recent_turns,
                "turn_count": loaded.conversation.turn_count,
            },
            "previous_retrieval": {
                "query": loaded.retrieval.query,
                "keywords": loaded.retrieval.keywords,
                "lesson_titles": loaded.retrieval.lesson_titles,
                "chunks": loaded.retrieval.chunks,
            },
            "steps": [step("tool", "load_memory",
                           (time.perf_counter() - started) * 1000,
                           turns=loaded.conversation.turn_count,
                           had_retrieval=loaded.retrieval.is_usable())],
        }

    # ------------------------------------------------------------------

    def understand(state: AgentState) -> dict:
        started = time.perf_counter()
        conversation, retrieval = _rehydrate(state)
        u = brain.understand(state["query"], conversation, retrieval)

        patch = {
            "route": u.route,
            "search_query": u.normalized_query,
            "understanding": u.model_dump(),
            "steps": [step("decision", "understand",
                           (time.perf_counter() - started) * 1000,
                           route=u.route, followup=u.is_followup,
                           confidence=round(u.confidence, 2), why=u.reasoning)],
        }

        if u.preferences:
            merged = dict(state.get("conversation", {}))
            merged["preferences"] = {**merged.get("preferences", {}), **u.preferences}
            patch["conversation"] = merged

        if u.route == "clarify":
            patch["clarification"] = u.clarification_question
            patch["reason"] = "needs_clarification"

        return patch

    # ------------------------------------------------------------------

    def small_talk(state: AgentState) -> dict:
        started = time.perf_counter()
        reply = brain.greet(state["query"], _rehydrate(state)[0])
        return {
            "answer": reply,
            "steps": [step("decision", "greet",
                           (time.perf_counter() - started) * 1000)],
        }

    # ------------------------------------------------------------------

    def plan_retrieval(state: AgentState) -> dict:
        started = time.perf_counter()
        conversation, retrieval = _rehydrate(state)
        plan = brain.plan_retrieval(
            state["understanding"], conversation, retrieval,
            has_docs=bool(state.get("doc_ids")),
        )
        return {
            "retrieval_plan": plan.model_dump(),
            "search_query": plan.search_query,
            "budget": plan.budget,
            "attempt": 0,
            "steps": [step("decision", "plan_retrieval",
                           (time.perf_counter() - started) * 1000,
                           retrieve=plan.should_retrieve,
                           reuse=plan.reuse_previous, query=plan.search_query,
                           budget=plan.budget, why=plan.reasoning)],
        }

    # ------------------------------------------------------------------

    def reuse_retrieval(state: AgentState) -> dict:
        result, patch = _call(state, "reuse_previous_retrieval", {})
        if result.ok:
            return {**patch, "chunks": result.data["chunks"],
                    "reused_retrieval": True}

        logger.info("reuse requested but unavailable; searching instead")
        return {**patch, "reused_retrieval": False}

    # ------------------------------------------------------------------

    def resolve_lesson_title(state: AgentState) -> dict:
        result, patch = _call(state, "list_lesson_titles",
                              {"doc_ids": state.get("doc_ids", [])})
        if not result.ok or not result.data["titles"]:
            return patch

        names = [t["title"] for t in result.data["titles"]]
        started = time.perf_counter()
        hint = state["retrieval_plan"].get("lesson_title_hint") or state["search_query"]
        chosen, confidence = brain.choose_lesson_title(hint, names)

        return {
            **patch,
            "titles": names,
            "lesson_title": chosen,
            "title_confidence": confidence,
            "steps": patch["steps"] + [
                step("decision", "choose_lesson_title",
                     (time.perf_counter() - started) * 1000,
                     hint=hint, chose=chosen, confidence=confidence)],
        }

    # ------------------------------------------------------------------

    def retrieve(state: AgentState) -> dict:
        plan = state["retrieval_plan"]
        result, patch = _call(state, "hybrid_search", {
            "query": state["search_query"],
            "lesson_title": state.get("lesson_title", ""),
            "filters": plan.get("metadata_filters", {}),
            "budget": state.get("budget", 12),
            "doc_ids": state["doc_ids"] if plan.get("use_doc_filter", True) else [],
            "title_as": "boost",
        })

        patch["attempt"] = state.get("attempt", 0) + 1

        if not result.ok:
            return {**patch, "errors": [f"search_failed:{result.error}"],
                    "reason": "no_relevant"}

        if result.data.get("user_has_no_documents"):
            return {**patch, "chunks": [], "reason": "no_documents"}

        return {**patch, "chunks": result.data["chunks"]}

    # ------------------------------------------------------------------

    def evaluate(state: AgentState) -> dict:
        started = time.perf_counter()
        verdict = brain.evaluate_retrieval(
            state["search_query"], state.get("chunks", []), state.get("attempt", 1))

        patch = {
            "verdict": verdict.model_dump(),
            "steps": [step("decision", "evaluate_retrieval",
                           (time.perf_counter() - started) * 1000,
                           attempt=state.get("attempt"),
                           sufficient=verdict.sufficient,
                           action=verdict.next_action,
                           missing=verdict.missing_concepts,
                           why=verdict.reasoning)],
        }

        if verdict.next_action == "rewrite" and verdict.rewritten_query:
            patch["search_query"] = verdict.rewritten_query
        elif verdict.next_action == "widen":
            patch["budget"] = min(state.get("budget", 12) * 2,
                                  settings.max_chunk_budget)

            patch["lesson_title"] = ""

        return patch


    def plan_quiz(state: AgentState) -> dict:
        started = time.perf_counter()
        plan = brain.plan_quiz(state["query"], state["chunks"],
                               _rehydrate(state)[0])
        return {
            "quiz_plan": plan.model_dump(),
            "steps": [step("decision", "plan_quiz",
                           (time.perf_counter() - started) * 1000,
                           qtype=plan.qtype, count=plan.count,
                           difficulty=plan.difficulty, bloom=plan.bloom_level,
                           why=plan.reasoning)],
        }

    def generate_questions(state: AgentState) -> dict:
        plan = state["quiz_plan"]
        previous = state.get("conversation", {}).get("preferences", {}).get("asked", [])

        result, patch = _call(state, "generate_questions", {
            "chunks": state["chunks"], "prompt": state["query"],
            "qtype": plan["qtype"], "count": plan["count"],
            "difficulty": plan["difficulty"], "previous": previous,
            "doc_ids": state.get("doc_ids", []),
        })
        if not result.ok:
            return {**patch, "errors": [f"generation_failed:{result.error}"]}

        questions = result.data["questions"]
        conversation = dict(state.get("conversation", {}))
        prefs = dict(conversation.get("preferences", {}))
        prefs["asked"] = (previous + [q["question"] for q in questions])[-40:]
        conversation["preferences"] = prefs

        return {**patch, "questions": questions,
                "practice_set_id": result.data["practice_set_id"],
                "conversation": conversation}


    def plan_answer(state: AgentState) -> dict:
        started = time.perf_counter()
        plan = brain.plan_answer(state["query"], _rehydrate(state)[0])
        return {
            "answer_plan": plan.model_dump(),
            "steps": [step("decision", "plan_answer",
                           (time.perf_counter() - started) * 1000,
                           style=plan.style, why=plan.reasoning)],
        }

    def generate_answer(state: AgentState) -> dict:
        plan = state.get("answer_plan", {})
        result, patch = _call(state, "generate_answer", {
            "chunks": state["chunks"], "question": state["query"],
            "style": plan.get("style", ""),
        })
        if not result.ok:
            return {**patch, "errors": [f"generation_failed:{result.error}"]}

        out = {**patch, "answer": result.data["answer"],
               "citations": result.data["citations"]
               if plan.get("include_citations", True) else []}

        if not result.data["sufficient"]:
            out["reason"] = "not_in_source"
        return out


    def mark(state: AgentState) -> dict:
        result, patch = _call(state, "mark_submission",
                              {"submission": state["submission"]})
        if not result.ok:
            return {**patch, "errors": [f"marking_failed:{result.error}"]}
        return {**patch, "route": "mark",
                "results": result.data["results"],
                "total_marks": result.data["total_marks"],
                "total_max": result.data["total_max"],
                "answer": result.data.get("summary", "")}


    def save_memory(state: AgentState) -> dict:
        started = time.perf_counter()
        user_id = UUID(state["user_id"])
        session_id = state["session_id"]

        if state.get("chunks") and not state.get("reused_retrieval"):
            memory.save_retrieval(user_id, session_id, RetrievalSnapshot(
                query=state.get("search_query", state["query"]),
                keywords=state.get("retrieval_plan", {}).get("keywords", []),
                filters={},
                lesson_titles=sorted({c.get("title", "") for c in state["chunks"]
                                      if c.get("title")}),
                doc_ids=state.get("doc_ids", []),
                chunks=state["chunks"],
                plan=state.get("retrieval_plan", {}),
            ))

        conversation, _ = _rehydrate(state)
        assistant_text = state.get("answer") or state.get("clarification") or ""

        if assistant_text and memory.conversation.needs_summary(conversation):
            conversation.summary, conversation.active_topic = \
                brain.summarise_conversation(conversation, state["query"], assistant_text)

        memory.save_conversation(user_id, session_id, conversation,
                                 state["query"], assistant_text)

        return {"steps": [step("tool", "save_memory",
                               (time.perf_counter() - started) * 1000)]}


    return {
        "load_memory": load_memory,
        "understand": understand,
        "small_talk": small_talk,
        "plan_retrieval": plan_retrieval,
        "reuse_retrieval": reuse_retrieval,
        "resolve_lesson_title": resolve_lesson_title,
        "retrieve": retrieve,
        "evaluate": evaluate,
        "plan_quiz": plan_quiz,
        "generate_questions": generate_questions,
        "plan_answer": plan_answer,
        "generate_answer": generate_answer,
        "mark": mark,
        "save_memory": save_memory,
    }


# ---------------------------------------------------------------------------
# state <-> memory objects
# ---------------------------------------------------------------------------

def _rehydrate(state: AgentState):
    """State holds plain dicts, because LangGraph serialises it to the
    checkpointer. The brain wants the memory objects. One place converts."""
    from memory.conversation import ConversationState
    from memory.retrieval import RetrievalSnapshot as Snap

    return (ConversationState(**state.get("conversation", {})),
            Snap(**state.get("previous_retrieval", {})))


# ---------------------------------------------------------------------------
# edges — pure functions of state, no side effects
# ---------------------------------------------------------------------------

def route_after_understand(state: AgentState) -> str:
    """
    The LLM's route decision, turned into an edge.
    """
    route = state.get("route", "answer")
    if route == "clarify":
        return "clarify"
    if route == "chat":
        return "chat"
    return "retrieve"


def route_after_plan(state: AgentState) -> str:
    plan = state.get("retrieval_plan", {})
    if not plan.get("should_retrieve", True):
        return "generate"
    if plan.get("reuse_previous"):
        return "reuse"
    if plan.get("lesson_title_hint"):
        return "resolve_title"
    return "search"


def route_after_reuse(state: AgentState) -> str:
    """Reuse succeeded, or fall through to a real search."""
    return "generate" if state.get("reused_retrieval") else "search"


def route_after_retrieve(state: AgentState) -> str:
    if state.get("reason") == "no_documents":
        return "save"
    return "evaluate"


def route_after_evaluate(state: AgentState) -> str:
    """
    The retry loop, as a conditional edge.
    """
    verdict = state.get("verdict", {})

    if verdict.get("sufficient") or verdict.get("next_action") == "proceed":
        return "generate"
    if verdict.get("next_action") == "give_up":
        return "generate"
    if state.get("attempt", 0) >= settings.max_retrieval_attempts:
        return "generate"
    if state.get("tool_calls", 0) >= settings.max_tool_calls:
        return "generate"
    return "retry"


def route_to_generator(state: AgentState) -> str:
    """Questions or prose — and neither if there is nothing to work from."""
    if not state.get("chunks"):
        return "save"
    return "questions" if state.get("route") == "questions" else "answer"
