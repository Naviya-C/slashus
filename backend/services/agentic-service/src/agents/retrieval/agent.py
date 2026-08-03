"""Retrieval agent: understand -> search (via MCP) -> rerank -> evaluate ->
refine loop. Registered as the "retrieve" agent.

Searches through the vector-store MCP client, passing the detected language so
the MCP server routes to the right Qdrant database. Writes `chunks` and
`language` into the context for downstream agents.
"""

from __future__ import annotations

import logging

from agents.base import Agent, AgentContext, Capability, register
from agents.retrieval.planning import make_plan
from agents.retrieval.ranking import Reranker, diversify, fuse_bm25
from agents.retrieval.understanding import QueryUnderstanding
from core.config import settings
from core.llm import QwenClient, LLMClient
from evaluator import EvaluatorService
from vectorstore import SearchRequest, VectorClient, build_vector_client

logger = logging.getLogger(__name__)


@register
class RetrievalAgent(Agent):
    name = "retrieve"
    capability = Capability.RETRIEVE

    def __init__(self, vector_client: VectorClient | None = None,
                 llm: LLMClient | QwenClient | None = None,
                 evaluator: EvaluatorService | None = None) -> None:
        # Groq, not Gemini. Query understanding and the evaluator run on
        # EVERY retrieval attempt — up to max_retries+1 times per question —
        # so on Gemini's 20-requests-per-day free tier a handful of questions
        # exhausts the quota and every subsequent evaluation silently returns
        # confidence 0.0. Groq's free tier is 1,000/day.
        llm = llm or QwenClient()
        self._understanding = QueryUnderstanding(llm)
        self._reranker = Reranker(llm)
        self._evaluator = evaluator or EvaluatorService(llm)
        self._vectors = vector_client or build_vector_client()

    def run(self, ctx: AgentContext) -> None:
        understanding = self._understanding.understand(ctx.query)
        ctx.language = understanding.language
        plan = make_plan(understanding)
        
        # Code debuging purpose I add this after that remove
        
        logger.info("plan: budget=%d filters=%r query=%r",
            plan.chunk_budget, plan.metadata_filters, understanding.normalized_query)
        

        plan.metadata_filters["user_id"] = str(ctx.user_id)
        doc_ids = ctx.get("doc_ids", [])
        if doc_ids:
            plan.metadata_filters["doc_id"] = [str(d) for d in doc_ids]

        current = understanding.normalized_query
        tried: list[str] = []
        best_hits: list = []
        best_quality = -1.0 

        for attempt in range(1, settings.max_retries + 2):
            limit = max(plan.chunk_budget, int(plan.chunk_budget * settings.overfetch_factor))
            resp = self._vectors.search(SearchRequest(
                query=current,
                language=understanding.language,   # routes to the right DB
                limit=limit,
                filters=plan.metadata_filters,
                mode="hybrid",
            ))
            hits = resp.hits

            # BM25 fusion, always on: free, local, no API call. Dense finds
            # chunks that MEAN the same thing; BM25 finds chunks containing
            # the same WORDS. For a study assistant the second matters —
            # a student asking about a specific term wants the passage using
            # it, not a semantically adjacent one.
            if hits:
                hits = fuse_bm25(current, hits)

            if plan.enable_reranking and hits:
                # Rerank only the head. At max_chunk_budget the overfetch can
                # reach 600 hits, which is a 600KB prompt and blows the
                # context window. Reranking past ~30 has almost no effect on
                # what survives diversify() anyway.
                head = hits[:settings.rerank_top_k]
                hits = self._reranker.rerank(current, head) + hits[settings.rerank_top_k:]
            hits = diversify(hits, plan.chunk_budget)

            if current not in tried:
                tried.append(current)

            chunk_dicts = [{"chunk_id": h.chunk_id, "content": h.content} for h in hits]
            report, control = self._evaluator.evaluate_rag(ctx.query, chunk_dicts)
            next_action = control.get("next_action", "return")
            rewritten = control.get("rewritten_query")
            logger.info(
                "retrieve attempt %d [%s/%s]: hits=%d passed=%s conf=%.2f action=%s%s",
                attempt, resp.language_used, resp.collection_used, len(hits),
                report.passed, report.confidence, next_action,
                # Without this marker, conf=0.00 looks like a retrieval
                # problem when it means the judge never ran.
                " (UNJUDGED)" if report.summary == "evaluator unavailable" else "",
            )

            quality = (1.0 if report.passed else 0.0) + report.confidence
            if quality > best_quality:
                best_quality, best_hits = quality, hits

            done = (
                (report.passed and report.confidence >= settings.min_confidence_to_stop)
                or next_action == "return"
                or attempt > settings.max_retries
            )
            if done:
                break

            if next_action == "rewrite_query" and rewritten:
                if rewritten in tried:
                    break
                current = rewritten
            elif next_action == "increase_budget":
                plan.chunk_budget = min(plan.chunk_budget * 2, settings.max_chunk_budget)
            elif next_action == "relax_filters":
                # Drops CONTENT filters the planner inferred, never the
                # ownership ones. Clearing the dict outright would widen the
                # search to every user's documents — the evaluator asking for
                # broader recall must not become a data leak.
                plan.metadata_filters = {
                    k: v for k, v in plan.metadata_filters.items()
                    if k in ("user_id", "doc_id")
                }

        ctx.put(
            # Survives the generator popping `chunks`, so the orchestrator can
            # tell "retrieval found nothing" apart from "retrieval worked and
            # something downstream failed" — which previously produced a
            # "re-upload your documents" message for a JSON parsing bug.
            retrieved_count=len(best_hits),
            chunks=[
                {"chunk_id": h.chunk_id, "content": h.content, "title": h.title,
                 "page": h.page, "score": h.score, "source": h.source}
                for h in best_hits
            ],
            query_used=current,
            language=understanding.language,
        )
