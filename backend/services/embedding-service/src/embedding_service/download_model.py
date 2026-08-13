"""Download the configured dense model into the FastEmbed cache."""

from __future__ import annotations

import os

from fastembed import TextEmbedding

from embedding_service.encoders.bge_m3 import BGE_M3_MODEL, register_model


def main() -> None:
    model_name = os.getenv("EMBEDDING_MODEL_NAME", BGE_M3_MODEL)
    register_model(model_name)
    TextEmbedding(model_name=model_name, threads=1)


if __name__ == "__main__":
    main()
