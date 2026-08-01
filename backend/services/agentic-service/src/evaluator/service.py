"""Shared Evaluator service.

ONE evaluator, called by multiple agents (per your choice): the retrieval
agent calls `evaluate_rag`, the generator calls `evaluate_questions` and
`evaluate_answers`. Centralizing the judgement keeps quality criteria
consistent across the system and gives a single place to tune them.

Loosely coupled: agents depend on this service's methods (a small surface),
not on the individual checkers.
"""

from __future__ import annotations

from core.llm import QwenClient, LLMClient
from evaluator.checks import AnswerChecker, QuestionChecker, RAGChecker
from evaluator.schemas import EvaluationReport


class EvaluatorService:
    def __init__(self, llm: LLMClient | QwenClient | None = None) -> None:
        # Groq by default. The evaluator runs on every retrieval attempt, so
        # on Gemini's free tier (20/day) it is the first thing to hit the
        # quota — and when it does, evaluate_rag returns confidence 0.0,
        # which reads as "retrieval found nothing useful" rather than "the
        # evaluator could not run".
        llm = llm or QwenClient()
        self._rag = RAGChecker(llm)
        self._questions = QuestionChecker(llm)
        self._answers = AnswerChecker(llm)

    def evaluate_rag(self, query: str, chunks: list[dict]):
        """Returns (EvaluationReport, control) where control drives the
        retrieval loop's next action."""
        return self._rag.check(query, chunks)

    def evaluate_questions(self, questions: list[dict], sources: str) -> EvaluationReport:
        return self._questions.check(questions, sources)

    def evaluate_answers(self, qa_pairs: list[dict], sources: str) -> EvaluationReport:
        return self._answers.check(qa_pairs, sources)
