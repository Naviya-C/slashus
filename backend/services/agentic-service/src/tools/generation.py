"""
tools/generation.py
===================

Generation and marking, as tools.

The LLM decides WHETHER to generate questions, how many, what type, and at
what difficulty — that is the quiz plan. These execute it: render the right
template, validate the output, persist, return.

WHY VALIDATION STAYS IN PYTHON
------------------------------
`normalize_questions` drops an MCQ with no `correct_index`, an option index
pointing past the end of the list, and a written question with no rubric.
Those are not judgement calls the model should be asked to make about its own
output — they are structural invariants the database has constraints for, and
a question that violates one cannot be marked later. Better to drop it at
generation than to fail at submission, when the student has already written
an answer.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from services.normalize import MCQ_TYPES, VALID_TYPES, normalize_questions
from prompts import pool
from tools.base import Tool, ToolError, ToolRegistry, clamp_int

logger = logging.getLogger(__name__)

_MAX_CHARS_PER_CHUNK = 1200
_MAX_CHUNKS = 16
_MAX_COUNT = 10


def format_sources(chunks: list[dict[str, Any]]) -> str:
    """Numbered, so the model can cite by position and the page numbers in its
    output can be checked against what was actually supplied."""
    return "\n\n".join(
        f"[{i}] (page {c.get('page', '?')}) {str(c.get('content', ''))[:_MAX_CHARS_PER_CHUNK]}"
        for i, c in enumerate(chunks[:_MAX_CHUNKS], 1)
    )


def register_generation_tools(registry: ToolRegistry, generator, marker) -> None:

    def generate_questions(*, user_id: UUID, session_id: str,
                           chunks: list, prompt: str, qtype: str = "mcq",
                           count: int = 5, difficulty: str = "medium",
                           previous: list | None = None,
                           doc_ids: list | None = None) -> dict[str, Any]:
        if not chunks:
            # Generating from no source produces confident invented content —
            # the worst possible failure for a study tool, because it is
            # indistinguishable from the real thing to the student.
            raise ToolError("no source material")

        if qtype not in VALID_TYPES:
            qtype = "mcq"
        count = clamp_int(count, 5, 1, _MAX_COUNT)
        template = "GENERATE_MCQ" if qtype in MCQ_TYPES else "GENERATE_WRITTEN"

        data = generator.llm.generate_json(
            pool.render(
                template,
                count=count,
                qtype=qtype,
                difficulty=difficulty,
                previous="\n".join(f"- {q}" for q in (previous or [])) or "(none)",
                sources=format_sources(chunks),
            ),
            # 0.7 here, unlike every other call in the system. Five questions
            # at temperature 0 come out as five rephrasings of the same one.
            temperature=0.7,
        )

        questions = normalize_questions(data.get("questions", []), qtype)
        if not questions:
            raise ToolError("every generated question failed validation")

        practice_set_id = generator.persist(
            user_id=user_id, session_id=session_id, prompt=prompt,
            doc_ids=doc_ids or [], questions=questions,
        )
        return {"questions": questions, "practice_set_id": practice_set_id,
                "qtype": qtype, "difficulty": difficulty}

    def generate_answer(*, user_id: UUID, session_id: str, chunks: list,
                        question: str, style: str = "") -> dict[str, Any]:
        if not chunks:
            raise ToolError("no source material")

        data = generator.llm.generate_json(
            pool.render("ANSWER", question=question,
                        sources=format_sources(chunks), style=style or "(default)"),
            temperature=0.3,
        )

        # The model returns which numbered sources it used. Indices outside
        # the supplied range are dropped rather than clamped: a citation
        # pointing at the wrong page is worse than no citation, because the
        # student follows it and finds nothing.
        used = [i for i in data.get("used", [])
                if isinstance(i, int) and 1 <= i <= len(chunks)]

        return {
            "answer": str(data.get("answer", "")).strip(),
            # Page and title ONLY, never chunk text. That gives the student
            # somewhere to look without shipping copyrighted passages to a
            # browser where they could be scraped a page at a time.
            "citations": [{"page": chunks[i - 1].get("page"),
                           "title": chunks[i - 1].get("title")} for i in used],
            "sufficient": bool(data.get("sufficient", True)),
        }

    def mark_submission(*, user_id: UUID, session_id: str,
                        submission: list) -> dict[str, Any]:
        if not submission:
            raise ToolError("nothing to mark")
        return marker.mark(user_id=user_id, submission=submission)

    registry.add(Tool(
        name="generate_questions",
        description="Create a practice set from retrieved material and save it",
        args={"qtype": "mcq | true_false | short | structured | essay",
              "count": "1-10", "difficulty": "easy | medium | hard",
              "previous": "questions already shown, so a continuation differs"},
        run=generate_questions,
    ))
    registry.add(Tool(
        name="generate_answer",
        description="Answer, explain or summarise from retrieved material, with citations",
        args={"question": "what to answer", "style": "any length or tone preference"},
        run=generate_answer,
    ))
    registry.add(Tool(
        name="mark_submission",
        description="Mark submitted answers against the stored questions and rubrics",
        args={"submission": "list of {question_id, selected_index | answer_text}"},
        run=mark_submission,
    ))
