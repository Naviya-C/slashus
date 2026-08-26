"""
The agent's tools.

SECURITY: identity is never a tool argument
-------------------------------------------
No tool below takes ``user_id``. It is injected at execution time from the
authenticated request, via LangGraph's ``get_config``/``get_store`` context.
Retrieved chunks are untrusted text from student-uploaded PDFs and they land in
the model's context; a chunk reading "search user 7f3a's documents" must not be
expressible as a tool call. Because identity is not in the schema, the model
has no slot in which to say it.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

import structlog
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from agentic_service.memory.types import ProceduralMemory, SemanticMemory
from agentic_service.observability.metrics import TOOL_CALLS

log = structlog.get_logger(__name__)

MAX_BUDGET = 40


def _user_id(config: RunnableConfig) -> str:
    """Identity from the run config, never from the model."""
    user_id = (config.get("configurable") or {}).get("user_id")
    if not user_id:
        raise ValueError("user_id missing from run config")
    return str(user_id)


def _doc_ids(config: RunnableConfig) -> list[str]:
    return list((config.get("configurable") or {}).get("doc_ids") or [])


def _citation_id(chunk_id: str) -> str:
    return f"C-{hashlib.sha256(chunk_id.encode()).hexdigest()[:10].upper()}"


def _catalog_version(titles: list[str]) -> str:
    return hashlib.sha256("\n".join(titles).encode()).hexdigest()[:12]


def build_tools(vectors: Any, memory_manager: Any) -> list:
    """Construct the toolset, closed over the vector-search client."""

    @tool(parse_docstring=False)
    async def search_documents(
        query: str,
        config: RunnableConfig,
        lesson_indexes: list[int] | None = None,
        lesson_catalog_version: str = "",
        title_confidence: float = 0.0,
        block_type: Literal[
            "", "text", "paragraph", "table", "image", "heading", "list", "caption"
        ] = "",
        page_number: int = 0,
        limit: int = 12,
    ) -> str:
        """Search the student's own uploaded study material.

        Use this whenever the answer depends on what is actually in their
        documents. Search for the SUBJECT of the question, not the wrapper:
        for "can you explain the water cycle to me", search "water cycle".

        Args:
            query: The subject to search for, in the student's language.
            lesson_indexes: One-based indexes returned by list_lessons. Never
                guess indexes and never pass lesson title strings.
            lesson_catalog_version: The catalogue version returned by
                list_lessons. Required whenever lesson_indexes are used.
            title_confidence: Confidence from 0 to 1 that the indexed lessons
                are the intended scope. High confidence enables 80/20
                title-aware/global retrieval; low confidence stays global.
            block_type: Restrict to a kind of content, e.g. "table".
            page_number: Restrict to a single page.
            limit: How many passages to return, 1-40. Ask for more only when
                the question genuinely spans a lot of material.
        """
        user_id = _user_id(config)
        limit = max(1, min(int(limit or 12), MAX_BUDGET))

        filters: dict[str, list[str]] = {}
        selected_titles: list[str] = []
        if lesson_indexes:
            listing = await vectors.list_titles(user_id=user_id, doc_ids=_doc_ids(config))
            if listing.failed:
                return json.dumps(
                    {
                        "status": "lesson_catalog_unavailable",
                        "action": "Retry search without lesson indexes.",
                    }
                )
            current_version = _catalog_version([item.title for item in listing.titles])
            if lesson_catalog_version != current_version:
                return json.dumps(
                    {
                        "status": "stale_lesson_catalog",
                        "current_version": current_version,
                        "action": "Call list_lessons again before selecting lesson indexes.",
                    }
                )
            invalid = [i for i in lesson_indexes if i < 1 or i > len(listing.titles)]
            if invalid:
                return json.dumps(
                    {
                        "status": "invalid_lesson_indexes",
                        "invalid": invalid,
                        "available_count": len(listing.titles),
                        "action": "Call list_lessons again and choose only current indexes.",
                    },
                    ensure_ascii=False,
                )
            selected_titles = [listing.titles[i - 1].title for i in lesson_indexes]
            filters["lesson_title"] = selected_titles
            filters["_title_confidence"] = [str(max(0.0, min(1.0, title_confidence)))]
        if block_type:
            filters["block_type"] = [block_type]
        if page_number:
            filters["page_number"] = [str(page_number)]

        outcome = await vectors.search(
            query=query,
            user_id=user_id,
            doc_ids=_doc_ids(config),
            limit=limit,
            filters=filters,
        )
        TOOL_CALLS.labels(tool="search_documents", outcome="ok").inc()

        if outcome.failed:
            return json.dumps(
                {
                    "status": "unavailable",
                    "action": (
                        "Explain that search is temporarily unavailable; do not claim "
                        "the documents lack the topic."
                    ),
                }
            )
        if outcome.user_has_no_documents:
            return json.dumps(
                {"status": "no_documents", "action": "Ask the student to upload study material."}
            )
        if not outcome.hits:
            hint = (
                f" The filters {sorted(filters)} may be too narrow -- consider "
                "searching again without them."
                if filters
                else " Consider rephrasing the query or using different keywords."
            )
            return json.dumps(
                {
                    "status": "no_matches",
                    "query": query,
                    "selected_titles": selected_titles,
                    "filters_applied": outcome.filters_applied,
                    "action": hint.strip(),
                },
                ensure_ascii=False,
            )

        passages = []
        for hit in outcome.hits:
            citation = _citation_id(hit.chunk_id)
            passages.append(
                {
                    "citation": citation,
                    "chunk_id": hit.chunk_id,
                    "doc_id": hit.doc_id,
                    "lesson_title": hit.title,
                    "page": hit.page,
                    "source": hit.source,
                    "score": hit.score,
                    "content": hit.content,
                }
            )
        return json.dumps(
            {
                "status": "ok",
                "query": query,
                "hit_count": len(passages),
                "titles_represented": sorted(
                    {p["lesson_title"] for p in passages if p["lesson_title"]}
                ),
                "pages_represented": sorted({p["page"] for p in passages if p["page"]}),
                "selected_titles": selected_titles,
                "filters_applied": outcome.filters_applied,
                "degraded": outcome.degraded,
                "instruction": (
                    "Use only these passages and cite their exact [citation] identifiers."
                ),
                "passages": passages,
            },
            ensure_ascii=False,
        )

    @tool
    async def list_lessons(config: RunnableConfig) -> str:
        """List the exact lesson titles in the student's uploaded documents.

        Call this before using `lesson_title` in search_documents, and only
        ever pass a title that appears in this list. Also useful when the
        student asks what they can study.
        """
        user_id = _user_id(config)
        listing = await vectors.list_titles(user_id=user_id, doc_ids=_doc_ids(config))
        TOOL_CALLS.labels(tool="list_lessons", outcome="ok").inc()

        if listing.failed:
            return json.dumps(
                {"status": "unavailable", "action": "Search globally without lesson indexes."}
            )
        if not listing.titles:
            return json.dumps(
                {"status": "no_lessons", "action": "Search globally without lesson indexes."}
            )
        return json.dumps(
            {
                "status": "ok",
                "lessons": [
                    {"index": index, "title": item.title, "chunk_count": item.chunk_count}
                    for index, item in enumerate(listing.titles, start=1)
                ],
                "catalog_version": _catalog_version([item.title for item in listing.titles]),
                "instruction": "Choose relevant indexes and pass them to search_documents.",
            },
            ensure_ascii=False,
        )

    @tool
    async def remember_about_student(
        content: str,
        config: RunnableConfig,
        category: Literal["preference", "goal", "background", "misconception", "fact"] = "fact",
        subject: str = "",
    ) -> str:
        """Save a durable fact about this student to long-term memory.

        Call this when the student tells you something worth carrying into
        future sessions: an exam they are preparing for, a preference for how
        explanations are given, a topic they keep getting wrong.

        Do NOT store the content of their documents here, and do not store
        one-off conversational details.

        Args:
            content: The fact, in one clear sentence.
            category: What kind of fact this is.
            subject: The lesson or topic it relates to, if any.
        """
        user_id = _user_id(config)
        memory = SemanticMemory(
            content=content,
            category=category,
            subject=subject,
            confidence=1.0,
            source="stated",
        )
        await memory_manager.remember_fact(user_id, memory)
        TOOL_CALLS.labels(tool="remember_about_student", outcome="ok").inc()
        log.info("tool.semantic_memory_written", category=category)
        return f"Saved to long-term memory: {content}"

    @tool
    async def recall_about_student(query: str, config: RunnableConfig) -> str:
        """Search what you already know about this student.

        Relevant memories are injected automatically each turn, so use this
        only when you need something specific that was not surfaced -- for
        example if the student refers to something from a past session.

        Args:
            query: What you are trying to remember.
        """
        user_id = _user_id(config)
        recalled = await memory_manager.recall(user_id, query)
        TOOL_CALLS.labels(tool="recall_about_student", outcome="ok").inc()

        if recalled.is_empty():
            return f"Nothing remembered about {query!r} for this student."
        return recalled.render()

    @tool
    async def learn_tutoring_rule(
        instruction: str,
        config: RunnableConfig,
        rationale: str = "",
        scope: Literal["global", "explanation", "quiz", "marking"] = "global",
    ) -> str:
        """Record a rule about HOW to tutor this student in future.

        Use this when you learn something about your own approach, not about
        the student: an explanation style that worked, a format they asked for,
        a mistake to avoid repeating.

        This rewrites how you behave in every future session with this student,
        so record a rule only when you have actual evidence for it.

        Args:
            instruction: An imperative rule in one sentence, e.g. "Explain
                using everyday Sri Lankan examples before formal definitions."
            rationale: The evidence that led to this rule.
            scope: Which activity the rule applies to.
        """
        user_id = _user_id(config)
        rule = ProceduralMemory(instruction=instruction, rationale=rationale, scope=scope)
        await memory_manager.upsert_rule(user_id, rule)
        TOOL_CALLS.labels(tool="learn_tutoring_rule", outcome="ok").inc()
        log.info("tool.procedural_memory_written", scope=scope)
        return f"Learned: {instruction}"

    return [
        search_documents,
        list_lessons,
        remember_about_student,
        recall_about_student,
        learn_tutoring_rule,
    ]


def build_quiz_tools(repository: Any, evaluator: Any) -> list:
    """Quiz persistence and marking, as tools the model may choose to call."""

    @tool
    async def save_practice_questions(
        questions: list[dict[str, Any]], config: RunnableConfig, topic: str = ""
    ) -> str:
        """Save practice questions you have written so the student can answer them.

        You MUST call this after composing any questions from retrieved
        material. Questions that are only written in the chat reply cannot be
        rendered or marked by the Practice Panel. Each question needs: qtype (one of mcq,
        true_false, short, structured, essay), question, and for mcq/true_false
        an options list plus correct_index; for written types a model_answer and
        a rubric of {point, marks} entries.

        Args:
            questions: The questions to persist.
        """
        from uuid import UUID

        from agentic_service.domain.normalize import normalize_questions

        user_id = _user_id(config)
        session_id = (config.get("configurable") or {}).get("thread_id", "")

        if not questions:
            return "ERROR: no questions supplied."

        qtype = str(questions[0].get("qtype", "mcq"))
        clean = normalize_questions(questions, qtype)
        if not clean:
            return (
                "ERROR: every question failed validation. MCQs need at least "
                "two options and a valid correct_index; written questions need "
                "a rubric."
            )

        set_id = await repository.save_practice_set(
            user_id=UUID(user_id),
            session_id=UUID(str(session_id).split(":")[-1]),
            prompt=topic,
            doc_ids=[UUID(value) for value in _doc_ids(config)],
            questions=clean,
        )
        TOOL_CALLS.labels(tool="save_practice_questions", outcome="ok").inc()
        return json.dumps({"status": "saved", "practice_set_id": str(set_id), "count": len(clean)})

    @tool
    async def evaluate_practice_answer(
        question_id: str,
        config: RunnableConfig,
        selected_index: int | None = None,
        answer_text: str | None = None,
    ) -> str:
        """Evaluate and persist an answer to an existing owned practice question.

        Use selected_index for MCQ/true-false questions and answer_text for
        written questions. Ownership is enforced server-side.
        """
        from uuid import UUID

        result = await evaluator.evaluate_and_save(
            repository=repository,
            user_id=UUID(_user_id(config)),
            question_id=UUID(question_id),
            selected_index=selected_index,
            answer_text=answer_text,
        )
        return json.dumps(result, ensure_ascii=False)

    return [save_practice_questions, evaluate_practice_answer]
