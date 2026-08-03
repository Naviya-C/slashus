"""Shared Gemini client — one implementation for every agent."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from google import genai

from core.config import settings

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_reasoning(text: str) -> str:
    """Remove a reasoning model's scratchpad before JSON extraction.

    Qwen 3 emits <think>...</think> ahead of its answer. Brace-matching
    without stripping it finds braces INSIDE the reasoning and parses the
    wrong object — or, more often, finds none and fails outright.
    """
    text = _THINK_RE.sub("", text)
    # Truncation mid-reasoning leaves an unclosed tag, in which case
    # everything after it is incomplete thought, not answer.
    if "<think>" in text and "</think>" not in text:
        text = text.split("<think>")[0]
    return text.strip()


def extract_json(text: str) -> dict[str, Any]:
    text = _strip_reasoning(text)
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON in LLM response: {text[:200]!r}")


def json_call(llm, prompt: str, *, temperature: float = 0.0) -> dict[str, Any]:
    """Call generate_json on whichever client was injected.

    QwenClient takes a keyword-only `temperature`; LLMClient (Gemini) does
    not. Every retrieval call site wants temperature 0 — extraction and
    classification have one right answer and sampling only adds variance — but
    hardcoding the kwarg makes those call sites crash on a Gemini client, and
    omitting it silently samples at 0.3 on Qwen.

    Try the kwarg, fall back on TypeError. Narrow on purpose: a TypeError
    raised from INSIDE the LLM call would be swallowed by a bare except and
    retried at the wrong temperature.
    """
    try:
        return llm.generate_json(prompt, temperature=temperature)
    except TypeError as exc:
        if "temperature" not in str(exc):
            raise
        return llm.generate_json(prompt)


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.model = model or settings.gemini_model
        self._client = genai.Client(api_key=api_key or settings.gemini_api_key)

    def generate(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, settings.llm_max_attempts + 1):
            try:
                resp = self._client.models.generate_content(
                    model=self.model, contents=prompt
                )
                return resp.text or ""
            except Exception as exc:
                last_error = exc
                logger.warning("LLM call failed (attempt %d): %s", attempt, exc)
                if attempt < settings.llm_max_attempts:
                    time.sleep(settings.llm_backoff_seconds * attempt)
        raise RuntimeError("LLM call failed after retries") from last_error

    def generate_json(self, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        current = prompt
        for _ in range(settings.llm_max_attempts):
            text = self.generate(current)
            try:
                return extract_json(text)
            except ValueError as exc:
                last_error = exc
                current = prompt + "\n\nRespond with ONLY a single valid JSON object."
        raise RuntimeError("LLM returned invalid JSON after retries") from last_error
