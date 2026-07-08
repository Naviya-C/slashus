"""
adapters/llm_captioner.py
=========================

PURPOSE
-------
Real ImageCaptioner backed by Gemini vision (google-genai SDK). Sends the image
bytes to Gemini and returns a short description used as the image chunk's content
and embed text.

SDK NOTES
---------
- Current unified SDK: `from google import genai` (old google-generativeai is EOL).
- Inline image call shape (verified):
      types.Part.from_bytes(data=image_bytes, mime_type="image/png")
      client.models.generate_content(model=..., contents=[part, prompt])
- SDK + client imported LAZILY so this module loads even without the SDK
  installed (keeps fake-based tests runnable).
- MODEL NAME is a parameter -- confirm which flash model is live on your key.
- Inline bytes cap total request at ~20MB; for anything larger use the File API
  (a later concern; our filtered figures are small).
- API key from the environment (GEMINI_API_KEY / GOOGLE_API_KEY).
"""

from __future__ import annotations

DEFAULT_MODEL = "gemini-2.5-flash"  # confirm against your key; override in config

_PROMPT = (
    "You are describing a figure from a Sri Lankan educational document. The "
    "surrounding text may be Sinhala, English, or both. In 1-2 short sentences, "
    "describe what the figure shows and its purpose for a student. Be concrete; "
    "do not guess at unreadable text. Output only the description.\n\n"
    "{context}"
)


class GeminiImageCaptioner:
    """ImageCaptioner implemented with Gemini vision."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None) -> None:
        from google import genai  
        
        self._genai = genai
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self._model = model

    def caption(self, image_bytes: bytes, mime_type: str, context: str = "") -> str:
        ctx = f"Context: {context}\n\n" if context.strip() else ""
        prompt = _PROMPT.format(context=ctx)
        part = self._genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        resp = self._client.models.generate_content(
            model=self._model, contents=[part, prompt]
        )
        return (resp.text or "").strip()