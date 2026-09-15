"""
Coercion of raw LLM output into the shape the repository and API expect.

Deliberately dependency-free apart from logging. This is the layer most likely
to need a fix when a model starts returning something slightly different, and
it must be testable without an API key, a database, or a model load.

The prompts ask for a precise shape and models mostly comply. These are the
deviations that actually occur in practice options as bare strings, an index
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


def _option_text(option: Any) -> tuple[str, bool]:
    """Options arrive as bare strings or as {text, is_correct} dicts."""
    if isinstance(option, dict):
        return str(option.get("text") or "").strip(), option.get("is_correct") is True
    return str(option).strip(), False


def _build_choice(item: dict, q: dict) -> dict | None:
    options: list[str] = []
    flagged: list[int] = []
    for raw in q.get("options", []):
        text, is_correct = _option_text(raw)
        if not text:
            continue
        if is_correct:
            flagged.append(len(options))
        options.append(text)

    if len(options) < 2:
        log.warning("dropping MCQ with %d options", len(options))
        return None

    try:
        idx = int(q.get("correct_index", -1))
    except (TypeError, ValueError):
        idx = -1
    if not 0 <= idx < len(options) and len(flagged) == 1:
        idx = flagged[0]
    if not 0 <= idx < len(options):
        log.warning("dropping MCQ with out-of-range correct_index %r", q.get("correct_index"))
        return None

    item["options"] = [{"index": j, "text": t} for j, t in enumerate(options)]
    item["correct_index"] = idx
    item["explanation"] = str(q.get("explanation", "")).strip() or None
    return item


def _build_written(item: dict, q: dict) -> dict | None:
    item["model_answer"] = str(q.get("model_answer", "")).strip() or None

    rubric = []
    for r in q.get("rubric", []):
        # Rubric entries arrive as bare strings or as {point, marks} dicts.
        if isinstance(r, str):
            point, marks = r.strip(), 0.0
        elif isinstance(r, dict):
            point = str(r.get("point", "")).strip()
            try:
                marks = float(r.get("marks", 0))
            except (TypeError, ValueError):
                continue
        else:
            continue
        if not point:
            continue
        rubric.append({"point": point, "marks": marks})

    if rubric and all(r["marks"] == 0 for r in rubric):
        share = round(TOTAL_MARKS / len(rubric), 1)
        for r in rubric:
            r["marks"] = share

    if not rubric:
        log.warning("dropping written question with no rubric")
        return None

    total = sum(r["marks"] for r in rubric)
    if total > 0 and abs(total - TOTAL_MARKS) > 0.01:
        for r in rubric:
            r["marks"] = round(r["marks"] * TOTAL_MARKS / total, 1)

    item["rubric"] = rubric
    return item
