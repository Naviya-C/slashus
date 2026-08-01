"""
src/core/llm/qwen.py
====================
Alibaba Model Studio (DashScope) client, interface-compatible with LLMClient
and GroqClient.

Same shape as the others on purpose: `generate` and `generate_json` with the
same signatures, so every agent accepts any of the three without changes.

Uses the native dashscope SDK rather than the OpenAI-compatible endpoint,
because the native one exposes `enable_thinking` directly — which matters
here.

Qwen3.5 / Qwen3.6 series require MultiModalConversation (not Generation).
Calling Generation with those models returns: "url error, please check url！"
"""
from __future__ import annotations

import logging
import time
from typing import Any

import dashscope
from dashscope import MultiModalConversation

from core.config import settings
from core.llm.client import extract_json

logger = logging.getLogger(__name__)

# International endpoint (Singapore). The Mainland China one is a different
# host AND a different API key — a key from one will not work against the
# other, and the error is an unhelpful 401.
dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"

# Retrying these can never succeed: the request is wrong, not unlucky.
_NON_RETRYABLE = {400, 401, 403, 404}

def _normalize_content(content: Any) -> str:
    """MultiModalConversation returns list[{'text': ...}]; plain str is also fine."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # shapes: {"text": "..."} or {"type": "text", "text": "..."}
                text = item.get("text")
                if text is not None:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)

class QwenClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or settings.qwen_model
        self._api_key = api_key or settings.qwen_api_key
        if not self._api_key:
            raise RuntimeError("QWEN_API_KEY (DASHSCOPE_API_KEY) is not set")

    # ------------------------------------------------------------------
    def _call(self, prompt: str, temperature: float, json_mode: bool) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "api_key": self._api_key,
            "model": self.model,
            "messages": messages,
            "result_format": "message",
            "enable_thinking": False,
            "temperature": temperature,
        }
        if getattr(settings, "llm_max_output_tokens", None):
            kwargs["max_tokens"] = settings.llm_max_output_tokens
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        logger.info("DashScope model: %s", self.model)
        logger.info("DashScope url: %s", dashscope.base_http_api_url)

        response = MultiModalConversation.call(**kwargs)

        logger.info(
            "DashScope response: status=%s code=%s message=%s",
            response.status_code,
            response.code,
            response.message,
        )

        if response.status_code != 200:
            logger.error("Full DashScope response: %s", response)
            raise RuntimeError(
                f"DashScope {response.status_code} "
                f"[{response.code}]: {response.message}"
            )

        choices = getattr(response.output, "choices", None) or []
        if not choices:
            raise RuntimeError(f"DashScope returned no choices: {response}")

        raw = choices[0].message.content
        logger.debug(
            "DashScope content type=%s sample=%r",
            type(raw).__name__,
            str(raw)[:200],
        )
        return _normalize_content(raw)

    def _is_non_retryable(self, exc: Exception) -> bool:
        return any(f"DashScope {code}" in str(exc) for code in _NON_RETRYABLE)

    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(1, settings.llm_max_attempts + 1):
            try:
                return self._call(prompt, temperature, json_mode)
            except Exception as exc:
                if self._is_non_retryable(exc):
                    # A wrong model name or bad key is configuration, not bad
                    # luck. Three retries with backoff only delay the message.
                    logger.error(
                        "DashScope request rejected (not retryable): %s", exc
                    )
                    raise
                last_error = exc
                logger.warning(
                    "DashScope call failed (attempt %d): %s", attempt, exc
                )
                if attempt < settings.llm_max_attempts:
                    time.sleep(settings.llm_backoff_seconds * attempt)
        raise RuntimeError(
            "DashScope call failed after retries"
        ) from last_error

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        current = prompt
        for _ in range(settings.llm_max_attempts):
            text = self.generate(
                current, temperature=temperature, json_mode=True
            )
            try:
                return extract_json(text)
            except ValueError as exc:
                last_error = exc
                logger.warning(
                    "DashScope returned unparseable JSON: %r", text[:200]
                )
                current = (
                    prompt
                    + "\n\nRespond with ONLY a single valid JSON object."
                )
        raise RuntimeError(
            "DashScope returned invalid JSON after retries"
        ) from last_error