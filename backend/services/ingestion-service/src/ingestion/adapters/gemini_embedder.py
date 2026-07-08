"""
adapters/gemini_embedder.py
===========================

PURPOSE
-------
Embedder backed by Gemini (google-genai `embed_content`). Turns chunk text and
query text into dense vectors for Qdrant.

WHY TWO TASK TYPES
------------------
A question and its answer are often NOT semantically similar as plain text.
Gemini's task_type fixes this: embed chunks as RETRIEVAL_DOCUMENT and queries as
RETRIEVAL_QUERY, and the two land in a space where they match. Using the wrong
type (or none) measurably hurts retrieval. (This replaces the e5 passage/query
prefix trick.)

NOTES
-----
- Current SDK: `from google import genai`; call client.models.embed_content(
      model=..., contents=[...], config=EmbedContentConfig(task_type=..., ...)).
  Result: response.embeddings[i].values.
- MODEL default gemini-embedding-001 (text, GA). gemini-embedding-2 is multimodal
  (could embed figures directly) -- a later upgrade; keep model a parameter.
- output_dimensionality is optional (MRL): smaller = cheaper storage/faster ANN.
  Pick ONE value and keep it fixed -- it defines your Qdrant vector size.
- BATCH: embed_documents sends many texts per call (cheaper, fewer round trips).
- Gemini's token limit is large (~2048), so your chunk budget can grow well past
  512 -- size chunks to the embedder, not the old LaBSE cap.
- Lazy SDK import; API key from env (GEMINI_API_KEY / GOOGLE_API_KEY).
"""

from __future__ import annotations

DEFAULT_MODEL = "gemini-embedding-001"
DEFAULT_DIM = 3072  # fix this once; it is your Qdrant vector size


class GeminiEmbedder:
    """Embedder implemented with Gemini embed_content."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        output_dim: int = DEFAULT_DIM,
        api_key: str | None = None,
    ) -> None:
        from google import genai  # lazy
        self._genai = genai
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self._model = model
        self._dim = output_dim

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        from google.genai import types
        resp = self._client.models.embed_content(
            model=self._model,
            contents=texts,
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=self._dim),
        )
        return [e.values for e in resp.embeddings]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task_type="RETRIEVAL_QUERY")[0]