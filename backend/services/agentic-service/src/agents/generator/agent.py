"""
src/agents/generator/agent.py
=============================

Produces study material from retrieved chunks.

The GENERATE intent covers two very different outputs — a practice set the
student answers, and an explanation they read — so this agent first decides
which (ARTIFACT.md), then routes to the matching template.

That decision matters beyond wording: questions render in the right-hand
practice panel and answers render in the conversation. Getting it wrong puts
content where the user is not looking.

One template per output type rather than one prompt with conditional sections.
MCQs need distractor-quality rules that mean nothing for an essay; essays need
rubric construction that means nothing for an MCQ. A combined prompt is longer,
dilutes both, and every edit risks the other.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent, AgentContext, Capability, register
from agents.generator.normalize import MCQ_TYPES as _MCQ, VALID_TYPES as _VALID, normalize_questions
from core.llm.qwen import QwenClient
from prompts import pool

logger = logging.getLogger(__name__)

_MAX_CHARS_PER_CHUNK = 1200
_MAX_CHUNKS = 16
_MAX_COUNT = 10
_MCQ_TYPES = _MCQ
_VALID_TYPES = _VALID


def _format_sources(chunks: list[dict[str, Any]]) -> str:
    """Numbered so the model can cite by position, and so page numbers in the
    output can be checked against what was actually supplied."""
    return "\n\n".join(
        f"[{i}] (page {c.get('page', '?')}) {str(c.get('content', ''))[:_MAX_CHARS_PER_CHUNK]}"
        for i, c in enumerate(chunks[:_MAX_CHUNKS], 1)
    )


@register
class GeneratorAgent(Agent):
    name = "generate"
    capability = Capability.GENERATE

    def __init__(self, llm: QwenClient | None = None, repo=None) -> None:
        self._llm = llm or QwenClient()
        # Optional so the agent is unit-testable without a database. When
        # absent, questions are returned but not persisted — which breaks
        # deferred marking, so production must always supply one.
        self._repo = repo

    # ------------------------------------------------------------------

    def run(self, ctx: AgentContext) -> None:
        chunks = ctx.get("chunks", [])
        if not chunks:
            # Preflight should have caught this upstream. Guarding anyway:
            # generating from no source produces confident invented content,
            # which is the worst possible failure for a study tool.
            ctx.errors.append("no_chunks")
            return

        spec = self._detect_artifact(ctx.query)
        sources = _format_sources(chunks)

        if spec["artifact"] == "questions":
            self._make_questions(ctx, spec, sources)
        else:
            self._make_prose(ctx, spec["artifact"], sources, chunks)

        # Chunks have been consumed. Dropping them here means no later change
        # to response shaping can accidentally serialize copyrighted passages
        # to the browser.
        ctx.data.pop("chunks", None)

    # ------------------------------------------------------------------

    def _detect_artifact(self, message: str) -> dict[str, Any]:
        """Decide what to produce. Falls back to `answer` on failure.

        `answer` rather than `questions` is the safe default: an unwanted
        explanation is mildly annoying, whereas an unwanted practice set opens
        a panel the user did not ask for and buries their actual question.
        """
        try:
            data = self._llm.generate_json(
                pool.render("ARTIFACT", message=message), temperature=0.0
            )
        except Exception:
            logger.warning("artifact detection failed; defaulting to answer", exc_info=True)
            return {"artifact": "answer", "question_type": "mcq", "count": 5}

        artifact = str(data.get("artifact", "answer")).lower()
        if artifact not in {"questions", "answer", "summary", "flashcards"}:
            artifact = "answer"

        qtype = str(data.get("question_type", "mcq")).lower()
        if qtype not in _VALID_TYPES:
            qtype = "mcq"

        try:
            count = max(1, min(int(data.get("count", 5)), _MAX_COUNT))
        except (TypeError, ValueError):
            count = 5

        return {"artifact": artifact, "question_type": qtype, "count": count}

    # ------------------------------------------------------------------

    def _make_questions(self, ctx: AgentContext, spec: dict, sources: str) -> None:
        qtype = spec["question_type"]
        template = "GENERATE_MCQ" if qtype in _MCQ_TYPES else "GENERATE_WRITTEN"

        # Set by the orchestrator for GENERATE_MORE, so a continuation does
        # not restate what the student has already seen.
        previous = ctx.get("previous_questions", [])

        try:
            data = self._llm.generate_json(
                pool.render(
                    template,
                    count=spec["count"],
                    qtype=qtype,
                    previous="\n".join(f"- {q}" for q in previous) or "(none)",
                    sources=sources,
                ),

                temperature=0.7,
            )
        except Exception:
            logger.exception("question generation failed")
            ctx.errors.append("generation_failed")
            return

        questions = normalize_questions(data.get("questions", []), qtype)
        if not questions:
            ctx.errors.append("generation_empty")
            return

        practice_set_id = None
        if self._repo is not None:
            practice_set_id = self._repo.save_practice_set(
                user_id=ctx.user_id,
                session_id=ctx.session_id,
                prompt=ctx.query,
                doc_ids=ctx.get("doc_ids", []),
                questions=questions,
            )
            # Ids are assigned by the database, so the response can only
            # reference them after the write.
            saved = self._repo.get_practice_set(practice_set_id, ctx.user_id)
            if not saved:
                # Without ids the client cannot submit for marking — it would
                # send question_id="" and get a 422 with no clue why.
                logger.error("practice set %s vanished after write", practice_set_id)
                ctx.errors.append("persist_failed")
                return
            for q, saved_q in zip(questions, saved["questions"]):
                q["id"] = saved_q["id"]

        ctx.put(
            questions=questions,
            practice_set_id=str(practice_set_id) if practice_set_id else None,
            artifact="questions",
        )

    # ------------------------------------------------------------------

    def _make_prose(self, ctx: AgentContext, artifact: str,
                    sources: str, chunks: list[dict]) -> None:
        """Answer, summary, or flashcards — everything that renders in chat."""
        try:
            data = self._llm.generate_json(
                pool.render("ANSWER", question=ctx.query, sources=sources),
                temperature=0.3,
            )
        except Exception:
            logger.exception("answer generation failed")
            ctx.errors.append("generation_failed")
            return

        used = [
            i for i in data.get("used", [])
            if isinstance(i, int) and 1 <= i <= len(chunks)
        ]

        # Citations carry page and title ONLY, never chunk text. That gives
        # the student somewhere to look without handing over the passage.
        citations = [
            {
                "page": chunks[i - 1].get("page"),
                "title": chunks[i - 1].get("title"),
            }
            for i in used
        ]

        ctx.put(
            answer=str(data.get("answer", "")).strip(),
            citations=citations,
            grounded=bool(data.get("sufficient", True)),
            artifact=artifact,
        )

    # ------------------------------------------------------------------
