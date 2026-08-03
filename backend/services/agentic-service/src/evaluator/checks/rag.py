"""RAG evaluation: groundedness, hallucination, citation, completeness.

Judges whether retrieved chunks actually support answering a query — the
Evaluator's "RAG Evaluation" column in the spec.
"""

from __future__ import annotations

import logging
from string import Template

from core.llm import LLMClient
from evaluator.schemas import EvaluationReport

logger = logging.getLogger(__name__)

_PROMPT = Template(
    """You are a RAG retrieval evaluator. Judge whether the CHUNKS are
sufficient and grounded to answer the QUERY. Do not answer the query.

QUERY: $query
CHUNKS:
$chunks

Assess: groundedness (do chunks contain the needed facts?), completeness
(all parts of the query covered?), and relevance (no off-topic noise).

Return ONLY JSON:
{"passed": true, "confidence": 0.9,
 "reasons": ["..."], "next_action": "return|rewrite_query|relax_filters|increase_budget",
 "rewritten_query": null}
"""
)


class RAGChecker:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def check(self, query: str, chunks: list[dict]) -> tuple[EvaluationReport, dict]:
        listing = "\n\n".join(
            f"[{c.get('chunk_id','?')}] {c.get('content','')[:1000]}" for c in chunks
        ) or "(none)"
        try:
            d = self._llm.generate_json(_PROMPT.substitute(query=query, chunks=listing))
        except RuntimeError:
            # Fail OPEN: let the retrieved chunks through rather than
            # discarding good results because the judge was rate-limited.
            #
            # The summary matters — confidence 0.0 in the retrieval log is
            # otherwise indistinguishable from "these chunks are useless",
            # and that sends you debugging retrieval when the real problem is
            # an LLM quota.
            logger.warning("evaluator unavailable; passing chunks through unjudged")
            report = EvaluationReport(passed=True, confidence=0.0,
                                      summary="evaluator unavailable")
            return report, {"next_action": "return", "rewritten_query": None}

        report = EvaluationReport(
            passed=bool(d.get("passed", False)),
            confidence=float(d.get("confidence", 0.0)),
            summary="; ".join(d.get("reasons", [])),
        )
        control = {
            "next_action": d.get("next_action", "return"),
            "rewritten_query": d.get("rewritten_query"),
        }
        return report, control
