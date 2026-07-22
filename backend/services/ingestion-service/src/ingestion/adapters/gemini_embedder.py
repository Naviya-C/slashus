from google import genai
from google.genai import types
import time
from google.genai import errors

class GeminiEmbedder:
    MODEL = "gemini-embedding-001"
    DIMS = 3072
    BATCH = 48
    DELAY = 35.0        # seconds between requests — tune to your RPM limit

    def __init__(self, api_key: str):
        self._client = genai.Client(api_key=api_key)

    def _embed_batch(self, batch, attempts=5):
        for attempt in range(attempts):
            try:
                resp = self._client.models.embed_content(
                    model=self.MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                        output_dimensionality=self.DIMS,
                    ),
                )
                return [e.values for e in resp.embeddings]
            except errors.APIError as e:
                if e.code == 429 and attempt < attempts - 1:
                    wait = 2 ** attempt * 5     # 5s, 10s, 20s, 40s
                    time.sleep(wait)
                else:
                    raise

    def embed_documents(self, texts):
        out = []
        for i in range(0, len(texts), self.BATCH):
            out.extend(self._embed_batch(texts[i:i + self.BATCH]))
            time.sleep(self.DELAY)              # throttle proactively
        return out