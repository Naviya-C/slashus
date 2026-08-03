"""
agent/graph.py
==============

The reasoning flow.

    load_memory
        -> understand
        -> [clarify?]  -> done
        -> plan_retrieval
        -> retrieve            (search, or reuse what we already have)
        -> evaluate            -> rewrite -> retrieve   (loop)
        -> generate            (answer | questions | marking)
        -> save_memory

Every decision in that flow is made by the LLM (agent/brain.py). Every action
is executed by a tool (tools/). This module is the wiring: it calls the brain,
acts on what comes back, and enforces the budget.

WHY PLAIN PYTHON AND NOT LANGGRAPH
----------------------------------
The flow is linear with one loop. LangGraph earns its complexity when there is
real branching, parallelism, or persistence between steps — here it would add
a framework, a state-schema, and a debugging layer to express `for attempt in
range(3)`.

The nodes below are deliberately written as separate single-purpose methods
taking and returning WorkingMemory, so lifting them into LangGraph later is
mechanical if the flow ever grows branches worth the framework.

WHAT THE APPLICATION STILL DECIDES, AND WHY
-------------------------------------------
Three things, all of them safety rather than reasoning:

  * OWNERSHIP. user_id comes from the session, never from a decision. Chunks
    are untrusted text that end up inside decision prompts, so a chunk saying
    "search user 7f3a's documents" is a free attempt at data theft.
  * THE BUDGET. The loop stops after `max_tool_calls` whatever the brain says.
    A decision that keeps returning "rewrite" would otherwise bill in a circle.
  * VALIDATION. A generated MCQ with no correct answer is dropped, because the
    database has a constraint for it and an unmarkable question is discovered
    only after the student has written an answer.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from agent.brain import Brain
from agent.decisions import RetrievalPlan, Understanding
from core.config import settings
from memory import MemoryStore
from memory.retrieval import RetrievalSnapshot
from memory.working import WorkingMemory
from tools import ToolRegistry

logger = logging.getLogger(__name__)



class AgentGraph:
    def __init__(self, brain: Brain, tools: ToolRegistry,
                 memory: MemoryStore, repo=None) -> None:
        self._brain = brain
        self._tools = tools
        self._memory = memory
        self._repo = repo

    # ==================================================================

    def run(self, *, query: str, user_id: UUID, session_id: str,
            doc_ids: list[str] | None = None,
            submission: list | None = None) -> WorkingMemory:
        wm = WorkingMemory(query=query, user_id=str(user_id),
                           session_id=session_id, doc_ids=doc_ids or [],
                           max_tool_calls=settings.max_tool_calls)

        loaded = self._load_memory(wm, user_id, session_id)

        # Marking never goes through understanding. The student pressed a
        # submit button; there is no intent to infer, and asking an LLM to
        # confirm that would add a call and a failure mode to a path that is
        # already unambiguous.
        if submission:
            self._mark(wm, user_id, session_id, submission)
            return wm

        understanding = self._understand(wm, loaded)

        if understanding.route == "clarify":
            wm.clarification = understanding.clarification_question
            wm.reason = "needs_clarification"
            self._save_memory(wm, user_id, session_id, loaded,
                              understanding.clarification_question)
            return wm

        if understanding.route == "chat":
            # No documents needed. Answering a greeting from textbook chunks
            # is worse than answering it directly.
            wm.answer = self._small_talk(understanding)
            self._save_memory(wm, user_id, session_id, loaded, wm.answer)
            return wm

        plan = self._plan_retrieval(wm, understanding, loaded)
        self._retrieve(wm, plan, understanding, user_id, session_id, loaded)

        if wm.reason == "no_documents":
            self._save_memory(wm, user_id, session_id, loaded, "")
            return wm

        self._generate(wm, understanding, user_id, session_id, loaded)
        self._save_memory(wm, user_id, session_id, loaded, wm.answer or "")
        return wm

    # ==================================================================
    # nodes
    # ==================================================================

    def _load_memory(self, wm: WorkingMemory, user_id: UUID, session_id: str):
        t = time.perf_counter()
        loaded = self._memory.load(user_id, session_id)
        wm.record("tool", "load_memory", (time.perf_counter() - t) * 1000,
                  turns=loaded.conversation.turn_count,
                  had_retrieval=loaded.retrieval.is_usable())
        return loaded

    # ------------------------------------------------------------------

    def _understand(self, wm: WorkingMemory, loaded) -> Understanding:
        t = time.perf_counter()
        u = self._brain.understand(wm.query, loaded.conversation, loaded.retrieval)
        wm.record("decision", "understand", (time.perf_counter() - t) * 1000,
                  route=u.route, followup=u.is_followup,
                  confidence=round(u.confidence, 2), why=u.reasoning)
        wm.route = u.route
        wm.understanding = {"intent": u.intent, "route": u.route,
                            "is_followup": u.is_followup, "topic": u.topic,
                            "confidence": u.confidence}

        # Preferences the student stated are merged into conversation memory,
        # so "shorter answers please" applies to every later turn and not only
        # the one where they said it.
        if u.preferences:
            loaded.conversation.preferences.update(u.preferences)
        return u

    # ------------------------------------------------------------------

    def _plan_retrieval(self, wm: WorkingMemory, u: Understanding,
                        loaded) -> RetrievalPlan:
        t = time.perf_counter()
        plan = self._brain.plan_retrieval(u, loaded.conversation, loaded.retrieval,
                                          has_docs=bool(wm.doc_ids))
        wm.record("decision", "plan_retrieval", (time.perf_counter() - t) * 1000,
                  retrieve=plan.should_retrieve, reuse=plan.reuse_previous,
                  query=plan.search_query, budget=plan.budget, why=plan.reasoning)
        wm.retrieval_plan = {
            "should_retrieve": plan.should_retrieve,
            "reuse_previous": plan.reuse_previous,
            "search_query": plan.search_query,
            "keywords": plan.keywords,
            "budget": plan.budget,
        }
        return plan

    # ------------------------------------------------------------------

    def _retrieve(self, wm: WorkingMemory, plan: RetrievalPlan,
                  u: Understanding, user_id: UUID, session_id: str, loaded) -> None:
        if not plan.should_retrieve:
            return

        if plan.reuse_previous:
            result = self._call(wm, "reuse_previous_retrieval", {}, user_id, session_id)
            if result.ok:
                wm.chunks = result.data["chunks"]
                wm.reused_retrieval = True
                # No evaluation loop on reused material. It was already judged
                # sufficient on the turn that fetched it, and re-judging it
                # spends a call to reach the same conclusion.
                return
            # Falling through to a real search. The plan was reasonable; there
            # simply was no previous retrieval — first turn, or Redis evicted.
            logger.info("reuse requested but unavailable; searching instead")

        # Resolve a lesson title against the REAL list before searching. The
        # plan only carries a HINT, because at planning time the model has not
        # seen what lessons exist.
        if plan.lesson_title_hint:
            titles = self._call(wm, "list_lesson_titles",
                                {"doc_ids": wm.doc_ids}, user_id, session_id)
            if titles.ok and titles.data["titles"]:
                names = [t["title"] for t in titles.data["titles"]]
                wm.titles = names
                t = time.perf_counter()
                plan.lesson_title = self._brain.choose_lesson_title(
                    plan.lesson_title_hint or plan.search_query, names)
                wm.record("decision", "choose_lesson_title",
                          (time.perf_counter() - t) * 1000,
                          hint=plan.lesson_title_hint, chose=plan.lesson_title)

        query = plan.search_query
        budget = plan.budget

        for attempt in range(1, settings.max_retrieval_attempts + 1):
            if not wm.budget_left():
                wm.record("decision", "stop", reason="tool budget exhausted")
                break

            result = self._call(wm, "hybrid_search", {
                "query": query,
                "lesson_title": plan.lesson_title,
                "filters": plan.metadata_filters,
                "budget": budget,
                "doc_ids": wm.doc_ids if plan.use_doc_filter else [],
                "title_as": "boost",
            }, user_id, session_id)

            if not result.ok:
                wm.errors.append(f"search_failed:{result.error}")
                break

            if result.data.get("user_has_no_documents"):
                # Nothing indexed at all. Retrying cannot help, and the
                # student needs "upload a PDF" rather than "I couldn't find
                # that" — a different message entirely.
                wm.reason = "no_documents"
                wm.record("tool", "hybrid_search", detail="user has no indexed chunks")
                return

            wm.chunks = result.data["chunks"]

            t = time.perf_counter()
            verdict = self._brain.evaluate_retrieval(query, wm.chunks, attempt)
            wm.record("decision", "evaluate_retrieval",
                      (time.perf_counter() - t) * 1000,
                      attempt=attempt, sufficient=verdict.sufficient,
                      action=verdict.next_action, missing=verdict.missing_concepts,
                      why=verdict.reasoning)

            if verdict.sufficient or verdict.next_action == "proceed":
                return
            if verdict.next_action == "give_up":
                break

            if verdict.next_action == "rewrite":
                query = verdict.rewritten_query
            elif verdict.next_action == "widen":
                budget = min(budget * 2, settings.max_chunk_budget)
                # The lesson filter goes first when widening. It is the
                # narrowest constraint and the most likely to be the reason
                # the material is thin.
                plan.lesson_title = ""
                plan.metadata_filters = {}

        if not wm.chunks:
            wm.reason = "no_relevant"

    # ------------------------------------------------------------------

    def _generate(self, wm: WorkingMemory, u: Understanding,
                  user_id: UUID, session_id: str, loaded) -> None:
        if not wm.chunks:
            wm.reason = wm.reason or "no_relevant"
            return

        if u.route == "questions":
            t = time.perf_counter()
            quiz = self._brain.plan_quiz(wm.query, wm.chunks, loaded.conversation)
            wm.record("decision", "plan_quiz", (time.perf_counter() - t) * 1000,
                      qtype=quiz.qtype, count=quiz.count,
                      difficulty=quiz.difficulty, bloom=quiz.bloom_level,
                      why=quiz.reasoning)
            wm.quiz_plan = {"qtype": quiz.qtype, "count": quiz.count,
                            "difficulty": quiz.difficulty,
                            "bloom_level": quiz.bloom_level}

            previous = loaded.conversation.preferences.get("asked", [])
            result = self._call(wm, "generate_questions", {
                "chunks": wm.chunks, "prompt": wm.query, "qtype": quiz.qtype,
                "count": quiz.count, "difficulty": quiz.difficulty,
                "previous": previous, "doc_ids": wm.doc_ids,
            }, user_id, session_id)

            if not result.ok:
                wm.errors.append(f"generation_failed:{result.error}")
                return

            wm.questions = result.data["questions"]
            wm.practice_set_id = result.data["practice_set_id"]

            # Remembered so "5 more" produces genuinely new questions rather
            # than paraphrases of what the student just saw.
            asked = previous + [q["question"] for q in wm.questions]
            loaded.conversation.preferences["asked"] = asked[-40:]
            return

        t = time.perf_counter()
        style = self._brain.plan_answer(wm.query, loaded.conversation)
        wm.record("decision", "plan_answer", (time.perf_counter() - t) * 1000,
                  style=style.style, why=style.reasoning)

        result = self._call(wm, "generate_answer", {
            "chunks": wm.chunks, "question": wm.query, "style": style.style,
        }, user_id, session_id)

        if not result.ok:
            wm.errors.append(f"generation_failed:{result.error}")
            return

        wm.answer = result.data["answer"]
        wm.citations = result.data["citations"] if style.include_citations else []
        if not result.data["sufficient"]:
            # The generator judged its own sources inadequate. Trusted over
            # the retrieval evaluator's earlier verdict because it saw the
            # full text, not a 300-character preview.
            wm.reason = "not_in_source"

    # ------------------------------------------------------------------

    def _mark(self, wm: WorkingMemory, user_id: UUID, session_id: str,
              submission: list) -> None:
        wm.route = "mark"
        result = self._call(wm, "mark_submission",
                            {"submission": submission}, user_id, session_id)
        if not result.ok:
            wm.errors.append(f"marking_failed:{result.error}")
            return
        wm.results = result.data["results"]
        wm.answer = result.data.get("summary", "")

    # ------------------------------------------------------------------

    def _save_memory(self, wm: WorkingMemory, user_id: UUID, session_id: str,
                     loaded, assistant_text: str) -> None:
        t = time.perf_counter()

        if wm.chunks and not wm.reused_retrieval:
            self._memory.save_retrieval(user_id, session_id, RetrievalSnapshot(
                query=wm.retrieval_plan.get("search_query", wm.query),
                keywords=wm.retrieval_plan.get("keywords", []),
                filters={},
                lesson_titles=sorted({c.get("title", "") for c in wm.chunks
                                      if c.get("title")}),
                doc_ids=wm.doc_ids,
                chunks=wm.chunks,
                plan=wm.retrieval_plan,
            ))

        state = loaded.conversation
        if assistant_text and self._memory.conversation.needs_summary(state):
            state.summary, state.active_topic = self._brain.summarise_conversation(
                state, wm.query, assistant_text)

        self._memory.save_conversation(user_id, session_id, state,
                                       wm.query, assistant_text)
        wm.record("tool", "save_memory", (time.perf_counter() - t) * 1000)

    # ==================================================================

    def _call(self, wm: WorkingMemory, name: str, args: dict,
              user_id: UUID, session_id: str):
        wm.spend()
        result = self._tools.execute(name, args, user_id=user_id,
                                     session_id=session_id)
        wm.record("tool", name, result.ms, outcome=result.summary())
        return result

    @staticmethod
    def _small_talk(u: Understanding) -> str:
        return (u.normalized_query and
                "Hello. Ask me about anything in your uploaded documents — "
                "I can explain it or make practice questions from it.")


# ---------------------------------------------------------------------------

def build_agent(*, vector_client, repo, llm, scratch, generator, marker) -> AgentGraph:
    """Composition root."""
    from memory import build_memory_store
    from tools import build_tools

    memory = build_memory_store(scratch, repo)
    tools = build_tools(vector_client, repo, generator, marker, memory)
    return AgentGraph(Brain(llm), tools, memory, repo)
