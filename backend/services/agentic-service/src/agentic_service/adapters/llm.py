from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agentic_service.config.settings import LLMSettings
from agentic_service.observability.metrics import LLM_CALLS, LLM_TOKENS

log = structlog.get_logger(__name__)


def build_model(settings: LLMSettings) -> ChatOpenAI:
    if not settings.api_key:
        raise ValueError("LLM_API_KEY is not set")
    
    return ChatOpenAI(
        model=settings.model,
        api_key=SecretStr(settings.api_key.get_secret_value()),
        base_url=settings.base_url,
        temperature=settings.temperature,
        max_completion_tokens=settings.max_output_tokens,
        timeout=settings.request_timeout_seconds,
        max_retries=settings.max_retries,
        stream_usage=True,
    )


class JsonLLM:
    def __init__(self, model: ChatOpenAI) -> None:
        self._model = model

    async def ainvoke_json(self, prompt: str, *, label: str = "json") -> dict[str, Any]:
        response = await self._model.ainvoke(prompt, response_format={"type": "json_object"})
        if usage := getattr(response, "usage_metadata", None):
            LLM_TOKENS.labels(kind="prompt").inc(usage.get("input_tokens", 0))
            LLM_TOKENS.labels(kind="completion").inc(usage.get("output_tokens", 0))

        text = str(response.content).strip()
        
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start == -1 or end <= start:
                LLM_CALLS.labels(outcome="unparseable").inc()
                raise ValueError(f"no JSON object in {label} response") from None
            parsed = json.loads(text[start : end + 1])

        LLM_CALLS.labels(outcome="ok").inc()
        
        if not isinstance(parsed, dict):
            raise ValueError(f"{label} returned {type(parsed).__name__}, expected object")
        return parsed
