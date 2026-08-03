"""
agent/brain.py
==============

Every decision the LLM makes, in one place.

One method per decision, each rendering a prompt file and validating the JSON
back into a dataclass. Nothing here executes anything — no database, no gRPC,
no Qdrant. The brain returns a decision and the graph acts on it.

WHY SEPARATE CALLS AND NOT ONE BIG "AGENT" PROMPT
-------------------------------------------------
A single prompt asking for intent, route, keywords, filters, budget, question
type, count and difficulty in one JSON object is cheaper by one call and worse
in every other way:

  * more required fields means flakier JSON, and one malformed field takes the
    whole decision with it
  * the retrieval plan genuinely needs to see the retrieved titles, which do
    not exist yet at understanding time
  * a prompt that does four jobs does all four worse, and tuning one of them
    silently changes the other three

Separate calls also mean each decision is independently switchable and
independently debuggable — the reasoning trace shows which one was wrong.

WHY EVERY METHOD HAS A FALLBACK
-------------------------------
Rate limits happen mid-conversation. A decision that cannot be made should
degrade to the safe default and keep the turn alive, because the student is
waiting and a working degraded answer beats a 500. Every fallback is recorded
in the trace so a silent degradation is still visible.
"""

from __future__ import annotations

import logging

from agent.decisions import (
    AnswerPlan,
    QuizPlan,
    RetrievalPlan,
    RetrievalVerdict,
    Understanding,
)
from core.embedding import detect_language
from prompts import pool

logger = logging.getLogger(__name__)

_MAX_TITLES_IN_PROMPT = 40
_MAX_CHUNK_PREVIEW = 300
_MAX_CHUNKS_IN_PROMPT = 10


class Brain:
    def __init__(self, llm) -> None:
        self._llm = llm

    # ------------------------------------------------------------------

    def _json(self, template: str, **values) -> dict:
        return self._llm.generate_json(pool.render(template, **values), temperature=0.0)

    # ------------------------------------------------------------------

    def understand(self, query: str, conversation, retrieval) -> Understanding:
        """Intent, route, follow-up detection, clarification.

        Sees the conversation because "explain more" is only interpretable
        against what came before, and sees the previous retrieval because
        deciding whether a topic continues needs to know what was found.
        """
        try:
            data = self._json(
                "UNDERSTAND",
                query=query,
                conversation=conversation.as_prompt_block(),
                previous_retrieval=retrieval.describe(),
            )
        except Exception:
            logger.warning("understanding failed; defaulting to answer route",
                           exc_info=True)
            return Understanding(route="answer", normalized_query=query,
                                 confidence=0.0, reasoning="llm unavailable")

        u = Understanding.from_json(data, query)

        # "Normalize" is one word from "translate", and the model takes that
        # step often enough to matter: a Sinhala question comes back as fluent
        # English, gets embedded, and matches nothing in a Sinhala corpus. The
        # failure is invisible — retrieval just returns weak results.
        if detect_language(u.normalized_query) != detect_language(query):
            logger.warning("normalized query changed language; keeping the original")
            u.normalized_query = query

        return u

    # ------------------------------------------------------------------

    def plan_retrieval(self, understanding: Understanding, conversation,
                       retrieval, has_docs: bool) -> RetrievalPlan:
        try:
            data = self._json(
                "PLAN_RETRIEVAL",
                query=understanding.normalized_query,
                intent=understanding.route,
                is_followup="yes" if understanding.is_followup else "no",
                conversation=conversation.as_prompt_block(),
                previous_retrieval=retrieval.describe(),
                has_documents="yes" if has_docs else "no",
            )
        except Exception:
            logger.warning("retrieval planning failed; searching the raw query",
                           exc_info=True)
            return RetrievalPlan(search_query=understanding.normalized_query,
                                 reasoning="llm unavailable")

        return RetrievalPlan.from_json(data, understanding.normalized_query)

    # ------------------------------------------------------------------

    def choose_lesson_title(self, query: str, titles: list[str]) -> str:
        """Pick a REAL title, by index.

        The model returns a NUMBER, not a string. That is the entire point: a
        model asked for a title produces a plausible one rather than a real
        one, and exact-match filtering on it excludes a whole lesson while
        reporting success. An index into a list it was just given cannot be
        wrong that way — and an out-of-range index is treated as no match
        rather than clamped, because a clamped index is a silent wrong answer.
        """
        if not titles:
            return ""

        shortlist = titles[:_MAX_TITLES_IN_PROMPT]
        try:
            data = self._json(
                "CHOOSE_TITLE",
                query=query,
                titles="\n".join(f"{i}. {t}" for i, t in enumerate(shortlist, 1)),
            )
        except Exception:
            logger.warning("title choice failed", exc_info=True)
            return ""

        index = data.get("index")
        if index is None:
            return ""
        try:
            i = int(index) - 1
        except (TypeError, ValueError):
            return ""
        return shortlist[i] if 0 <= i < len(shortlist) else ""

    # ------------------------------------------------------------------

    def evaluate_retrieval(self, query: str, chunks: list[dict],
                           attempt: int) -> RetrievalVerdict:
        """Sufficient, or search again?

        Sees a PREVIEW of each chunk, not the whole thing. Judging sufficiency
        needs to know what the chunks are about; the full text would be ~15k
        characters of Sinhala per call to answer a yes/no question.
        """
        if not chunks:
            # No LLM call needed. Zero chunks is never sufficient, and asking
            # a model to confirm that costs a call and a second of latency.
            return RetrievalVerdict(sufficient=False, confidence=1.0,
                                    next_action="rewrite" if attempt < 2 else "give_up",
                                    reasoning="nothing retrieved")

        preview = "\n".join(
            f"[{i}] (p{c.get('page', '?')}) {str(c.get('content', ''))[:_MAX_CHUNK_PREVIEW]}"
            for i, c in enumerate(chunks[:_MAX_CHUNKS_IN_PROMPT], 1)
        )
        try:
            data = self._json("EVALUATE_RETRIEVAL", query=query,
                              chunks=preview, attempt=attempt)
        except Exception:
            # Proceed rather than retry. The chunks might be fine, and
            # spending the remaining budget on retries the evaluator cannot
            # judge just delays an answer the student may already have.
            logger.warning("retrieval evaluation unavailable; proceeding",
                           exc_info=True)
            return RetrievalVerdict(sufficient=True, confidence=0.0,
                                    reasoning="evaluator unavailable")

        return RetrievalVerdict.from_json(data)

    # ------------------------------------------------------------------

    def plan_quiz(self, query: str, chunks: list[dict], conversation) -> QuizPlan:
        titles = sorted({c.get("title", "") for c in chunks if c.get("title")})
        try:
            data = self._json(
                "PLAN_QUIZ",
                query=query,
                material=", ".join(titles) or "(untitled material)",
                chunk_count=len(chunks),
                conversation=conversation.as_prompt_block(),
            )
        except Exception:
            logger.warning("quiz planning failed; defaulting to 5 MCQs",
                           exc_info=True)
            return QuizPlan(reasoning="llm unavailable")

        return QuizPlan.from_json(data)

    # ------------------------------------------------------------------

    def plan_answer(self, query: str, conversation) -> AnswerPlan:
        try:
            data = self._json("PLAN_ANSWER", query=query,
                              conversation=conversation.as_prompt_block())
        except Exception:
            return AnswerPlan(reasoning="llm unavailable")
        return AnswerPlan.from_json(data)

    # ------------------------------------------------------------------

    def summarise_conversation(self, state, latest_user: str,
                               latest_assistant: str) -> tuple[str, str]:
        """Rolling summary + active topic. Returns the previous values on
        failure, so a failed summarisation loses an update rather than the
        whole memory."""
        try:
            data = self._json(
                "SUMMARISE",
                previous_summary=state.summary or "(none)",
                turns="\n".join(f"{t['role']}: {t['content'][:200]}"
                                for t in state.recent_turns[-4:]),
                latest_user=latest_user,
                latest_assistant=latest_assistant[:600],
            )
        except Exception:
            logger.warning("summarisation failed; keeping previous summary",
                           exc_info=True)
            return state.summary, state.active_topic

        return (str(data.get("summary") or state.summary).strip(),
                str(data.get("active_topic") or state.active_topic).strip())
