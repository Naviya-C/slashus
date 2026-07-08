"""
adapters/llm_summarizer.py
==========================

PURPOSE
-------
Real TableSummarizer backed by Gemini (google-genai SDK). Turns a markdown table
into a single retrieval-friendly sentence.

WHY A SUMMARY (not the raw grid)
--------------------------------
Embeddings are weak on tabular text -- a grid of short cells and numbers makes a
muddy vector. A sentence like "Rainfall by district, 2020-2023, five districts"
embeds cleanly and retrieves well. So we embed the summary and keep the markdown
as the returned content.

SDK NOTES
---------
- Uses the current unified SDK: `from google import genai`
  (the old google-generativeai reached end-of-life in Nov 2025).
- Call shape: client.models.generate_content(model=..., contents=...).
- The SDK + client are imported LAZILY so this module imports even where the SDK
  is not installed (keeps fake-based tests runnable).
- MODEL NAME is a parameter. Confirm which model is live on your key
  (e.g. gemini-2.5-flash / gemini-3.5-flash) and set it in config.
- API key comes from the environment (GEMINI_API_KEY / GOOGLE_API_KEY), read by
  the SDK -- never hardcode it.
"""

from __future__ import annotations

DEFAULT_MODEL = "gemini-2.5-flash"  

_PROMPT = (
    "You are summarising a table extracted from a Sri Lankan educational "
    "document. The text may be Sinhala, English, or both. In ONE short sentence "
    "(max ~30 words), say what the table shows: its subject, the main dimensions "
    "(rows/columns), and any range. Do not restate cells. Output only the sentence.\n\n"
    "If the table is hold sinhala major then summarize using sinhala."
    "Everytime use major language to summarize which table uses"
    "{context}"
    "Table (markdown):\n{markdown}"
)


class GeminiTableSummarizer:
    """TableSummarizer implemented with Gemini."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None) -> None:
        from google import genai  
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self._model = model

    def summarize(self, markdown: str, context: str = "") -> str:
        """
        markdown = The table which extracted from the extraction/table_extractor.py
            e.g:- |name|city|
        context = Any more information about the tables.
            e.g:- Figure 3.1. This is table......
        """
        
        ctx = f"Context: {context}\n\n" if context.strip() else ""
        prompt = _PROMPT.format(context = ctx, markdown = markdown)
        resp = self._client.models.generate_content(model=self._model, contents=prompt)
        text = (resp.text or "").strip()
        
        return text.splitlines()[0].strip() if text else ""