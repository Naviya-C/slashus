"""
agent/brain.py
==============
"""

from __future__ import annotations

import logging

from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from agent.decisions import (
    AnswerPlan,
    QuizPlan,
    RetrievalPlan,
    RetrievalVerdict,
    Understanding,
)
from core.embedding import detect_language
from core.retrieval.bm25 import BM25
from prompts import pool

logger = logging.getLogger(__name__)

_MAX_TITLES_IN_PROMPT = 40
_MAX_CHUNK_PREVIEW = 300
_MAX_CHUNKS_IN_PROMPT = 10


class Brain:
    def __init__(self, llm) -> None:
        self._llm = llm

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_not_exception_type((KeyError, FileNotFoundError)),
        reraise=True,
    )
    def _json(self, template: str, **values) -> dict:
        return self._llm.generate_json(pool.render(template, **values), temperature=0.0)


    def understand(self, query: str, conversation, retrieval) -> Understanding:
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

        u = Understanding.model_validate(data)
        if not u.normalized_query:
            u.normalized_query = query

        if detect_language(u.normalized_query) != detect_language(query):
            logger.warning("normalized query changed language; keeping the original")
            u.normalized_query = query

        return u

    def plan_retrieval(self, understanding, conversation,
                       retrieval, has_docs: bool) -> RetrievalPlan:

        if isinstance(understanding, dict):
            understanding = Understanding.model_validate(understanding)
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

        plan = RetrievalPlan.model_validate(data)
        if not plan.search_query:
            plan.search_query = understanding.normalized_query
        return plan

    def choose_lesson_title(self, query: str,
                                titles: list[str]) -> tuple[str, float]:
            if not titles:
                return "", 0.0

            ranked = BM25(titles).score(query)
            bm25_title, bm25_conf = "", 0.0
            if ranked:
                top = ranked[0].score
                second = ranked[1].score if len(ranked) > 1 else 0.0
                bm25_title = titles[ranked[0].index]
                bm25_conf = top / (top + second) if (top + second) else 0.0

            shortlist = titles
            if len(titles) > _MAX_TITLES_IN_PROMPT:
                if ranked:
                    shortlist = [titles[d.index] for d in ranked[:_MAX_TITLES_IN_PROMPT]]
                else:
                    shortlist = titles[:_MAX_TITLES_IN_PROMPT]

            llm_title, llm_conf = "", 0.0
            try:
                data = self._json(
                    "CHOOSE_TITLE",
                    query=query,
                    titles="\n".join(f"{i}. {t}" for i, t in enumerate(shortlist, 1)),
                )
                index = data.get("index")
                if index is not None:
                    i = int(index) - 1
                    if 0 <= i < len(shortlist):
                        llm_title = shortlist[i]
                        llm_conf = float(data.get("confidence", 0.5))
                        logger.info("title index %d of %d -> %r", i + 1, len(shortlist), llm_title)
                    else:
                        logger.warning("title index %r out of range", index)
            except Exception:
                logger.warning("title choice failed; falling back to BM25",
                            exc_info=True)

            llm_conf = max(0.0, min(llm_conf, 1.0))

            if llm_title and llm_title == bm25_title:
                confidence = min(1.0, (llm_conf + bm25_conf) / 2 + 0.15)
                chosen = llm_title
            elif llm_title:
                confidence = min(0.75, llm_conf * 0.8)
                chosen = llm_title
            elif bm25_conf >= 0.65:
                confidence = min(0.7, bm25_conf * 0.8)
                chosen = bm25_title
            else:
                return "", 0.0

            logger.info("title match %r conf=%.2f (llm=%.2f/%r bm25=%.2f/%r)",
                        chosen, confidence, llm_conf, llm_title, bm25_conf, bm25_title)
            
            return chosen, round(confidence, 2)
    

    def evaluate_retrieval(self, query: str, chunks: list[dict],
                           attempt: int) -> RetrievalVerdict:
        if not chunks:
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
            
            logger.warning("retrieval evaluation unavailable; proceeding",
                           exc_info=True)
            return RetrievalVerdict(sufficient=True, confidence=0.0,
                                    reasoning="evaluator unavailable")

        return RetrievalVerdict.model_validate(data)


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

        return QuizPlan.model_validate(data)


    def plan_answer(self, query: str, conversation) -> AnswerPlan:
        try:
            data = self._json("PLAN_ANSWER", query=query,
                              conversation=conversation.as_prompt_block())
        except Exception:
            return AnswerPlan(reasoning="llm unavailable")
        return AnswerPlan.model_validate(data)


    def greet(self, query: str, conversation) -> str:

        try:
            data = self._json("GREET", query=query,
                              conversation=conversation.as_prompt_block())
            reply = str(data.get("reply", "")).strip()
        except Exception:
            logger.warning("greeting generation failed", exc_info=True)
            reply = ""
            
        return reply or (
            "Hello. Ask me about anything in your uploaded documents — I can "
            "explain it or make practice questions from it."
        )

    # ------------------------------------------------------------------

    def summarise_conversation(self, state, latest_user: str,
                               latest_assistant: str) -> tuple[str, str]:

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
