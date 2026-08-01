"""Answer evaluation: correct, complete, consistent with source — the
Evaluator's "Answer Evaluation" column."""

from __future__ import annotations

import json
import logging
from string import Template

from core.llm import LLMClient
from evaluator.schemas import EvaluationReport, ItemScore, Verdict

logger = logging.getLogger(__name__)

_PROMPT = Template(
    """You evaluate answers against a SOURCE. For EACH answer judge: correct,
complete, consistent with source (no hallucination).

SOURCE:
$sources

Q&A PAIRS (JSON):
$pairs

Return ONLY JSON:
{"items": [{"id": "a0", "verdict": "pass|revise|fail", "score": 0.0, "reasons": ["..."]}],
 "passed": true, "confidence": 0.9}
"""
)


class AnswerChecker:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def check(self, qa_pairs: list[dict], sources: str) -> EvaluationReport:
        payload = json.dumps(
            [{"id": f"a{i}", "question": p.get("question", ""), "answer": p.get("answer", "")}
             for i, p in enumerate(qa_pairs)],
            ensure_ascii=False,
        )
        try:
            d = self._llm.generate_json(
                _PROMPT.substitute(sources=sources[:6000], pairs=payload)
            )
        except RuntimeError:
            return EvaluationReport(passed=True, confidence=0.0,
                                    item_scores=[ItemScore(f"a{i}", Verdict.PASS, 1.0)
                                                 for i in range(len(qa_pairs))])
        scores = []
        for it in d.get("items", []):
            try:
                v = Verdict(str(it.get("verdict", "pass")).lower())
            except ValueError:
                v = Verdict.PASS
            scores.append(ItemScore(str(it.get("id", "")), v,
                                    float(it.get("score", 0.0)),
                                    [str(r) for r in it.get("reasons", [])]))
        return EvaluationReport(passed=bool(d.get("passed", False)),
                                confidence=float(d.get("confidence", 0.0)),
                                item_scores=scores)
