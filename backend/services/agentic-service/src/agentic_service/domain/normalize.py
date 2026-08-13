"""Coercion of raw LLM output into the shape the repository and API expect.

Deliberately dependency-free apart from logging. This is the layer most likely
to need a fix when a model starts returning something slightly different, and
it must be testable without an API key, a database, or a model load.

The prompts ask for a precise shape and models mostly comply. These are the
deviations that actually occur in practice: options as bare strings, an index
returned as text, rubric marks that do not total 10, page numbers as words.
Handling them in one place means the database, the API and the frontend do not
each have to defend separately.
"""

from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger(__name__)

MCQ_TYPES = {"mcq", "true_false"}
VALID_TYPES = MCQ_TYPES | {"short", "structured", "essay"}
TOTAL_MARKS = 10


def normalize_questions(raw: list[dict], qtype: str) -> list[dict]:
    out: list[dict] = []

    for i, q in enumerate(raw):
        question = str(q.get("question", "")).strip()
        if not question:
            continue

        item: dict[str, Any] = {
            "position": i,
            "qtype": qtype,
            "question": question,
            "max_marks": TOTAL_MARKS,
            "source_pages": [int(p) for p in q.get("source_pages", []) if str(p).isdigit()],
        }

        built = _build_choice(item, q) if qtype in MCQ_TYPES else _build_written(item, q)
        if built is not None:
            out.append(built)

    return out


def _build_choice(item: dict, q: dict) -> dict | None:
    options = [str(o).strip() for o in q.get("options", []) if str(o).strip()]

    # Fewer than two choices is not a question. Dropped rather than shipped
    # broken — a student shown an unanswerable question loses trust in the
    # whole set.
    if len(options) < 2:
        log.warning("dropping MCQ with %d options", len(options))
        return None

    try:
        idx = int(q.get("correct_index", -1))
    except (TypeError, ValueError):
        idx = -1
    if not 0 <= idx < len(options):
        log.warning("dropping MCQ with out-of-range correct_index %r", q.get("correct_index"))
        return None

    # index stored explicitly rather than implied by array position, so the
    # frontend can shuffle options for display without breaking marking.
    item["options"] = [{"index": j, "text": t} for j, t in enumerate(options)]
    item["correct_index"] = idx
    item["explanation"] = str(q.get("explanation", "")).strip() or None
    return item


def _build_written(item: dict, q: dict) -> dict | None:
    item["model_answer"] = str(q.get("model_answer", "")).strip() or None

    rubric = []
    for r in q.get("rubric", []):
        point = str(r.get("point", "")).strip()
        if not point:
            continue
        try:
            marks = float(r.get("marks", 0))
        except (TypeError, ValueError):
            continue
        rubric.append({"point": point, "marks": marks})

    # A written question with no rubric cannot be marked consistently — the
    # marker would invent a standard per submission, so two students giving
    # the same answer could score differently.
    if not rubric:
        log.warning("dropping written question with no rubric")
        return None

    total = sum(r["marks"] for r in rubric)
    # Rescale rather than reject: the marks are proportionally right and only
    # the total drifts. Throwing away a good question over arithmetic wastes
    # an LLM call.
    if total > 0 and abs(total - TOTAL_MARKS) > 0.01:
        for r in rubric:
            r["marks"] = round(r["marks"] * TOTAL_MARKS / total, 1)

    item["rubric"] = rubric
    return item
