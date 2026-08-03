"""
services/generation.py
======================

Renders a generation template and persists the result. Decides nothing.

The type, count, difficulty and Bloom level all arrive from the agent's quiz
plan. What stays here is the part that is not a judgement call: validating the
structure and writing it to the database.
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class GenerationService:
    def __init__(self, llm, repo=None) -> None:
        # Public: tools/generation.py renders templates against it. Exposed
        # rather than wrapped because a wrapper would only forward, and the
        # prompt choice belongs with the tool that knows which template.
        self.llm = llm
        self._repo = repo

    def persist(self, *, user_id: UUID, session_id: str, prompt: str,
                doc_ids: list, questions: list[dict]) -> str | None:
        """Save a practice set and stamp the questions with their real ids.

        Without ids the client cannot submit for marking — it would send
        question_id="" and get a 422 with no clue why. So the ids are read
        back after the write and written onto the dicts in place.
        """
        if self._repo is None:
            logger.warning("no repository; questions will not be markable later")
            return None

        set_id = self._repo.save_practice_set(
            user_id=user_id, session_id=session_id, prompt=prompt,
            doc_ids=doc_ids, questions=questions,
        )
        saved = self._repo.get_practice_set(set_id, user_id)
        if not saved:
            logger.error("practice set %s vanished after write", set_id)
            return None

        for q, saved_q in zip(questions, saved["questions"]):
            q["id"] = saved_q["id"]
        return str(set_id)
