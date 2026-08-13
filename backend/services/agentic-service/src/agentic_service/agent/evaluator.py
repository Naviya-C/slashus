from __future__ import annotations

import json
from typing import Any
from uuid import UUID


class AnswerEvaluator:
    def __init__(self, llm: Any) -> None:
        self._llm = llm

    async def evaluate_and_save(
        self,
        *,
        repository: Any,
        user_id: UUID,
        question_id: UUID,
        selected_index: int | None,
        answer_text: str | None,
    ) -> dict[str, Any]:
        question = await repository.get_question(question_id=question_id, user_id=user_id)
        if question is None:
            raise ValueError("question does not exist or is not owned by this user")

        qtype = question["qtype"]
        maximum = int(question.get("max_marks") or 1)
        if qtype in {"mcq", "true_false"}:
            if selected_index is None:
                raise ValueError("selected_index is required for this question")
            correct = selected_index == question.get("correct_index")
            result = {
                "marks": maximum if correct else 0,
                "max_marks": maximum,
                "is_correct": correct,
                "feedback": question.get("explanation")
                or ("Correct." if correct else "Review the explanation and try again."),
                "revealed_answer": (
                    question.get("options", [])[question.get("correct_index")]
                    if question.get("correct_index") is not None
                    and question.get("correct_index") < len(question.get("options", []))
                    else str(question.get("correct_index"))
                ),
                "rubric_results": [],
            }
        else:
            if not (answer_text or "").strip():
                raise ValueError("answer_text is required for this question")
            rubric = question.get("rubric") or []
            prompt = (
                "Evaluate the student's answer only against the supplied rubric. "
                "Return JSON with marks, feedback, and rubric_results. Each rubric result "
                "must contain point, awarded_marks, max_marks, and feedback.\n\n"
                + json.dumps(
                    {
                        "question": question["question"],
                        "model_answer": question.get("model_answer"),
                        "rubric": rubric,
                        "max_marks": maximum,
                        "student_answer": answer_text,
                    },
                    ensure_ascii=False,
                )
            )
            judged = await self._llm.ainvoke_json(prompt, label="mark_written_answer")
            rubric_results = []
            total = 0.0
            for index, item in enumerate(rubric):
                candidate = judged.get("rubric_results") or [{}]
                raw = candidate[index] if index < len(candidate) else {}
                point_max = float(item.get("marks", 0))
                awarded = max(0.0, min(point_max, float(raw.get("awarded_marks", 0))))
                total += awarded
                rubric_results.append(
                    {
                        "point": item.get("point", ""),
                        "awarded_marks": awarded,
                        "max_marks": point_max,
                        "feedback": str(raw.get("feedback", "")),
                    }
                )
            result = {
                "marks": max(0.0, min(float(maximum), total)),
                "max_marks": maximum,
                "is_correct": None,
                "feedback": str(judged.get("feedback", "")),
                "revealed_answer": question.get("model_answer"),
                "rubric_results": rubric_results,
            }

        await repository.save_answer(
            question_id=question_id,
            user_id=user_id,
            selected_index=selected_index,
            answer_text=answer_text,
            result=result,
        )
        return {"question_id": str(question_id), **result}
