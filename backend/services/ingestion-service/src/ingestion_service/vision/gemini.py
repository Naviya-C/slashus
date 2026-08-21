from __future__ import annotations

from ingestion_service.config import Settings


_PROMPT = """Describe this educational image for semantic retrieval.
Use the dominant language visible in the image. Mention the subject, important
objects, labels, relationships, and educational purpose. Do not invent unreadable
details. Return no more than 60 words and no formatting."""


class GeminiCaptioner:
    def __init__(self, settings: Settings) -> None:
        if settings.gemini_api_key is None:
            raise ValueError("GEMINI_API_KEY is required for the vision worker")
        from google import genai

        self._genai = genai
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self._model = settings.vision_model

    def caption(self, data: bytes, content_type: str) -> str:
        part = self._genai.types.Part.from_bytes(data=data, mime_type=content_type)
        response = self._client.models.generate_content(
            model=self._model,
            contents=[part, _PROMPT],
        )
        return (response.text or "").strip()

