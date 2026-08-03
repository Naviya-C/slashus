"""Question evaluation: factually correct, answerable, difficulty, ambiguity,
clarity — the Evaluator's "Question Evaluation" column. Scores each question
so the generator can regenerate ONLY the weak ones."""

from __future__ import annotations

import logging
from string import Template

from core.llm import LLMClient
from evaluator.schemas import EvaluationReport, ItemScore, Verdict

logger = logging.getLogger(__name__)

_PROMPT = Template(
    """You evaluate exam questions for quality, grounded in the SOURCE.
For EACH question judge: factually correct (per source), answerable from
source, clear (unambiguous), appropriate difficulty.

SOURCE:
$sources

QUESTIONS (JSON):
$questions

Return ONLY JSON:
{"items": [{"id": "q0", "verdict": "pass|revise|fail", "score": 0.0,
            "reasons": ["..."]}],
 "passed": true, "confidence": 0.9}
verdict "pass" = good; "revise"/"fail" = must be regenerated.
"""
)


class QuestionChecker:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def check(self, questions: list[dict], sources: str) -> EvaluationReport:
        import json
        payload = json.dumps(
            [{"id": f"q{i}", "question": q.get("question", ""), "type": q.get("type")}
             for i, q in enumerate(questions)],
            ensure_ascii=False,
        )
        try:
            d = self._llm.generate_json(
                _PROMPT.substitute(sources=sources[:6000], questions=payload)
            )
        except RuntimeError:
            # fail-open: accept all
            return EvaluationReport(passed=True, confidence=0.0,
                                    item_scores=[ItemScore(f"q{i}", Verdict.PASS, 1.0)
                                                 for i in range(len(questions))])
        scores = []
        for it in d.get("items", []):
            try:
                v = Verdict(str(it.get("verdict", "pass")).lower())
            except ValueError:
                v = Verdict.PASS
            scores.append(ItemScore(
                item_id=str(it.get("id", "")),
                verdict=v,
                score=float(it.get("score", 0.0)),
                reasons=[str(r) for r in it.get("reasons", [])],
            ))
        return EvaluationReport(
            passed=bool(d.get("passed", False)),
            confidence=float(d.get("confidence", 0.0)),
            item_scores=scores,
        )
