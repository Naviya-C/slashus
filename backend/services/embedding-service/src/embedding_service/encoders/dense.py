"""Dense encoder: BGE-M3 via FastEmbed (ONNX Runtime).

WHY ONNX INSTEAD OF sentence-transformers
-----------------------------------------
The previous builds loaded BGE-M3 through ``sentence-transformers``, which
pulls in the full PyTorch runtime. On the 8 GB CPU VM this deployment targets,
that is the dominant cost in the process:

  * torch + CUDA-less wheels are ~800 MB of dependencies and several hundred MB
    of resident memory before a single vector is produced.
  * PyTorch spawns its own intra-op thread pool, which then competes with the
    gRPC handlers and the Kafka consumer in the same process for the same
    cores.

FastEmbed runs the same weights through ONNX Runtime: substantially smaller
install, lower resident memory, faster CPU inference, and an explicit thread
count rather than a pool that grabs whatever it finds. It also removes the
`sentence-transformers` -> `transformers` -> `torch` chain from the image
entirely.

Inference is still dispatched to a bounded executor. ONNX inference releases
the GIL but is CPU-bound; running it inline on the event loop stalls every
concurrent request for the duration of the forward pass.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import structlog

from embedding_service.config.settings import EmbeddingSettings

if TYPE_CHECKING:
    from fastembed import TextEmbedding

log = structlog.get_logger(__name__)


class DenseEncoder:
    """BGE-M3 dense embeddings.

    Note there is NO "query: " prefix. That is an E5 convention; BGE-M3 is
    trained without instruction prefixes, and adding one to queries only means
    queries and documents land in different distributions -- a silent, uniform
    loss of recall. Prefixes stay configurable for models that do want them.
    """

    def __init__(self, settings: EmbeddingSettings | None = None) -> None:
        self._cfg = settings or EmbeddingSettings()
        self._model: TextEmbedding | None = None
        self._executor = ThreadPoolExecutor(
            max_workers=self._cfg.inference_workers, thread_name_prefix="dense"
        )
        # Bounds the queue explicitly. Without it a burst builds an unbounded
        # backlog of futures and the symptom is memory growth, not a clear
        # rejection.
        self._gate = asyncio.Semaphore(self._cfg.inference_workers)

    @property
    def dimensions(self) -> int:
        return self._cfg.dimensions

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    async def warmup(self) -> None:
        """Load and run one forward pass before declaring readiness.

        Loading eagerly means the readiness probe stays red until the service
        can actually serve, instead of the first request after a deploy
        absorbing a multi-second stall.
        """
        if self._model is not None:
            return

        def _load() -> TextEmbedding:
            from fastembed import TextEmbedding

            return TextEmbedding(
                model_name=self._cfg.model_name,
                threads=self._cfg.onnx_threads,
                # int8 roughly halves memory and speeds up CPU inference, at a
                # small and generally acceptable recall cost. Off by default so
                # enabling it is a deliberate, measurable decision.
                quantized=self._cfg.quantized,
            )

        loop = asyncio.get_running_loop()
        log.info(
            "dense.loading",
            model=self._cfg.model_name,
            quantized=self._cfg.quantized,
            threads=self._cfg.onnx_threads,
        )
        self._model = await loop.run_in_executor(self._executor, _load)

        probe = await self.embed_documents(["warmup"])
        if len(probe[0]) != self._cfg.dimensions:
            raise RuntimeError(
                f"{self._cfg.model_name} produced {len(probe[0])} dims, "
                f"expected {self._cfg.dimensions}"
            )
        log.info("dense.ready", dimensions=self._cfg.dimensions)

    def _encode_sync(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:  # pragma: no cover - guarded by warmup()
            raise RuntimeError("dense encoder used before warmup()")
        return [
            list(map(float, vector))
            for vector in self._model.embed(texts, batch_size=self._cfg.encode_batch_size)
        ]

    async def _encode(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        async with self._gate:
            return await loop.run_in_executor(self._executor, self._encode_sync, texts)

    def _truncate(self, text: str) -> str:
        return text[: self._cfg.max_text_length]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._encode([self._cfg.document_prefix + self._truncate(t) for t in texts])

    async def embed_query(self, text: str) -> list[float]:
        return (await self._encode([self._cfg.query_prefix + self._truncate(text)]))[0]

    async def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._model = None
