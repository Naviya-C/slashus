"""
services/marking.py
===================

Marks submitted answers. Two paths, deliberately separate:

  MCQ / true-false  integer comparison against the stored correct_index. No
                    LLM. Exact, instant, free, and it cannot be talked out of
                    the right answer by a confident wrong submission.

  written           MARK_WRITTEN.md against the rubric stored WITH the
                    question at generation time — not re-derived per
                    submission, so every student is graded to the same
                    standard.

Both read from the database rather than trusting the client's copy of the
question. The frontend holds correct_index for instant feedback, but the
authoritative mark is computed here; otherwise a submission could claim any
question text and any correct answer it liked.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from prompts import pool

logger = logging.getLogger(__name__)

# Below this the student sees the model answer. A learning threshold, not a
# grade boundary — see MARK_WRITTEN.md.
_REVEAL_BELOW = 5.0
_MAX_CHARS_PER_CHUNK = 1200


class MarkingService:
    def __init__(self, llm, repo=None) -> None:
        self._llm = llm
        self._repo = repo

    # ------------------------------------------------------------------

    def mark(self, *, user_id: UUID, submission: list) -> dict[str, Any]:
        if self._repo is None:
            raise RuntimeError("marking requires a repository")

        results: list[dict[str, Any]] = []
        weak: list[str] = []

        for item in submission:
            question_id = item.get("question_id")
            if not question_id:
                continue

            # Scoped by user_id: question ids travel to the browser, so a
            # submission could name someone else's question. Returns None
            # rather than raising when it is not this user's.
            question = self._repo.get_question(UUID(question_id), user_id)
            if question is None:
                logger.warning("submission for unknown/foreign question %s", question_id)
                continue

            if question["qtype"] in {"mcq", "true_false"}:
                result = self._mark_choice(question, item)
            else:
                result = self._mark_written(question, item)

            self._repo.save_answer(
                question_id=UUID(question_id), user_id=user_id,
                selected_index=item.get("selected_index"),
                answer_text=item.get("answer_text"), result=result,
            )
            results.append(result)

            if result["marks"] < result["max_marks"] * 0.5:
                weak.append(question["question"][:80])

        if not results:
            raise RuntimeError("nothing to mark")

        total = round(sum(r["marks"] for r in results), 1)
        out_of = sum(r["max_marks"] for r in results)

        return {
            "results": results,
            "total_marks": total,
            "total_max": out_of,
            # Fed back into conversation memory, so a later "give me practice"
            # can target what the student actually got wrong.
            "weak_areas": weak,
            "summary": f"{total} out of {out_of}.",
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _mark_choice(question: dict, item: dict) -> dict[str, Any]:
        """Exact comparison. All marks or none — there is no partial credit in
        choosing one of four options."""
        selected = item.get("selected_index")
        correct = question["correct_index"]
        is_correct = selected is not None and int(selected) == int(correct)

        return {
            "question_id": str(question["id"]),
            "marks": float(question["max_marks"]) if is_correct else 0.0,
            "max_marks": question["max_marks"],
            "is_correct": is_correct,
            # The explanation was generated with the question and teaches
            # regardless of outcome — a student who guessed right still needs
            # to know why.
            "feedback": question.get("explanation") or (
                "Correct." if is_correct else "That's not right."),
            "rubric_breakdown": [],
            "revealed_answer": None if is_correct else question["options"][correct]["text"],
        }

    # ------------------------------------------------------------------

    def _mark_written(self, question: dict, item: dict) -> dict[str, Any]:
        answer = str(item.get("answer_text", "")).strip()

        if not answer:
            # Short-circuit before the LLM. An empty answer scores zero
            # whatever a model says about it.
            return self._zero(question, "No answer was submitted.",
                              question.get("model_answer"))

        # The chunks the question was WRITTEN from, not a fresh retrieval.
        # Re-retrieving at marking time surfaces different passages, and then
        # the marker grades against material the question was never based on.
        sources = self._repo.get_question_sources(question["id"])

        try:
            data = self._llm.generate_json(
                pool.render(
                    "MARK_WRITTEN",
                    question=question["question"],
                    rubric="\n".join(f"- ({r['marks']} marks) {r['point']}"
                                     for r in question.get("rubric", [])),
                    model_answer=question.get("model_answer") or "(none supplied)",
                    sources="\n\n".join(
                        str(s.get("content", ""))[:_MAX_CHARS_PER_CHUNK]
                        for s in sources) or "(source material unavailable)",
                    answer=answer,
                ),
                # Marking must be reproducible: the same answer gets the same
                # mark twice. That is the whole reason for temperature 0.
                temperature=0.0,
            )
        except Exception:
            logger.exception("written marking failed")
            # Distinguished from a genuine zero, so the frontend can offer a
            # retry rather than showing a failing mark for a server problem.
            return self._zero(question, "Marking failed. Please try again.", None)

        marks = max(0.0, min(float(data.get("marks", 0)), float(question["max_marks"])))

        # The reveal decision is made HERE, not taken from the model. It is
        # asked for in the prompt, but a threshold rule is not something to
        # leave to a generation that might ignore it.
        reveal = marks < _REVEAL_BELOW

        return {
            "question_id": str(question["id"]),
            "marks": round(marks, 1),
            "max_marks": question["max_marks"],
            # None, not a bool: a written answer is graded on a scale, and
            # forcing it to correct/incorrect throws away what the mark says.
            "is_correct": None,
            "feedback": str(data.get("feedback", "")).strip(),
            "rubric_breakdown": data.get("rubric_breakdown", []),
            "revealed_answer": question.get("model_answer") if reveal else None,
        }

    @staticmethod
    def _zero(question: dict, feedback: str, reveal: str | None) -> dict[str, Any]:
        # No extra keys: api/server.py does QuestionResult(**r), so anything
        # not on that dataclass raises TypeError — which once turned one
        # recoverable marking failure into a 500 for the whole submission,
        # including questions that marked fine.
        return {
            "question_id": str(question["id"]),
            "marks": 0.0,
            "max_marks": question["max_marks"],
            "is_correct": None,
            "feedback": feedback,
            "rubric_breakdown": [],
            "revealed_answer": reveal,
        }
