# adapters/local_embedder.py
from sentence_transformers import SentenceTransformer

class LocalEmbedder:
    """DenseEmbedder port — BGE-M3, runs on CPU/GPU, zero rate limits."""
    MODEL = "BAAI/bge-m3"
    DIMS = 1024

    def __init__(self):
        self._model = SentenceTransformer(self.MODEL)

    def embed_documents(self, texts):
        return self._model.encode(texts, batch_size=16,
                                  normalize_embeddings=True).tolist()

    def embed(self, query: str):                  # agent side
        return self._model.encode(f"query: {query}",
                                  normalize_embeddings=True).tolist()