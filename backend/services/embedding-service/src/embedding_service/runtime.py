"""Composition root and supervisor.

One event loop running three tasks under a TaskGroup: gRPC, HTTP probes, and
the Kafka consumer. A task that dies is observed and marks its component
unhealthy -- readiness goes red and the orchestrator routes away -- rather than
calling os._exit and skipping every cleanup path.
"""

from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass

import structlog
import uvicorn

from embedding_service.api.app import create_app
from embedding_service.config.settings import Settings, get_settings
from embedding_service.encoders.dense import DenseEncoder
from embedding_service.encoders.sparse import SinhalaSparseEncoder
from embedding_service.grpcapi.server import build_server, set_serving
from embedding_service.grpcapi.servicer import VectorSearchServicer
from embedding_service.messaging.consumer import ChunkConsumer
from embedding_service.observability.health import ComponentState, HealthRegistry
from embedding_service.observability.logging import configure_logging
from embedding_service.observability.tracing import configure_tracing
from embedding_service.store.ingest import IngestService
from embedding_service.store.qdrant import QdrantStore
from embedding_service.store.search import SearchService

log = structlog.get_logger(__name__)


@dataclass(slots=True)
class Container:
    settings: Settings
    health: HealthRegistry
    store: QdrantStore
    dense: DenseEncoder
    sparse: SinhalaSparseEncoder
    ingest: IngestService
    search: SearchService
    redis: object | None = None

    @classmethod
    def build(cls, settings: Settings | None = None) -> Container:
        cfg = settings or get_settings()
        health = HealthRegistry()
        store = QdrantStore(cfg.qdrant, cfg.retrieval)
        dense = DenseEncoder(cfg.embedding)
        sparse = SinhalaSparseEncoder(
            num_buckets=cfg.sparse.num_buckets,
            seed=cfg.sparse.seed,
            min_token_length=cfg.sparse.min_token_length,
            k1=cfg.sparse.tf_k1,
        )
        redis_client = None
        if cfg.redis.url:
            import redis.asyncio as aioredis

            redis_client = aioredis.from_url(cfg.redis.url, decode_responses=True)
        return cls(
            settings=cfg,
            health=health,
            store=store,
            dense=dense,
            sparse=sparse,
            ingest=IngestService(
                settings=cfg, store=store, dense=dense, sparse=sparse, redis=redis_client
            ),
            search=SearchService(settings=cfg, store=store, dense=dense, sparse=sparse),
            redis=redis_client,
        )

    async def aclose(self) -> None:
        await self.dense.close()
        await self.store.close()
        if self.redis is not None:
            await self.redis.aclose()


class Supervisor:
    def __init__(self, container: Container) -> None:
        self._c = container
        self._shutdown = asyncio.Event()

    def _on_signal(self, sig: signal.Signals) -> None:
        log.info("shutdown.signal", signal=sig.name)
        # Readiness red first so the load balancer drains this instance while
        # in-flight work finishes.
        self._c.health.begin_shutdown()
        self._shutdown.set()

    async def run(self) -> None:
        c = self._c
        cfg = c.settings

        for component in ("dense-model", "qdrant", "grpc-server", "kafka-consumer", "http-server"):
            c.health.register(component)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._on_signal, sig)

        c.health.set("dense-model", ComponentState.STARTING, "loading")
        await c.dense.warmup()
        c.health.set("dense-model", ComponentState.HEALTHY, cfg.embedding.model_name)

        if await c.store.ping():
            try:
                await c.store.ensure_collection(cfg.qdrant.collection, cfg.embedding.dimensions)
                c.health.set("qdrant", ComponentState.HEALTHY, cfg.qdrant.collection)
            except Exception as exc:
                c.health.set("qdrant", ComponentState.FAILED, str(exc)[:200])
                raise
        else:
            # Degraded, not failed: killing the process here turns a dependency
            # blip into a restart loop.
            c.health.set("qdrant", ComponentState.DEGRADED, "unreachable at startup")

        servicer = VectorSearchServicer(
            settings=cfg, search=c.search, dense=c.dense, sparse=c.sparse
        )
        grpc_server, health_servicer = await build_server(servicer, cfg.server)

        app = create_app(settings=cfg, health=c.health)
        http_server = uvicorn.Server(
            uvicorn.Config(
                app,
                host=cfg.server.http_host,
                port=cfg.server.http_port,
                log_config=None,
                access_log=False,
            )
        )
        http_server.install_signal_handlers = lambda: None  # type: ignore[method-assign]
        consumer = ChunkConsumer(settings=cfg, ingest=c.ingest, health=c.health)

        async def run_grpc() -> None:
            await grpc_server.start()
            await set_serving(health_servicer, True)
            c.health.set("grpc-server", ComponentState.HEALTHY, f":{cfg.server.grpc_port}")
            log.info("grpc.serving", port=cfg.server.grpc_port)
            await self._shutdown.wait()

        async def run_http() -> None:
            c.health.set("http-server", ComponentState.HEALTHY, f":{cfg.server.http_port}")
            task = asyncio.create_task(http_server.serve())
            await self._shutdown.wait()
            http_server.should_exit = True
            await task

        async def run_consumer() -> None:
            task = asyncio.create_task(consumer.run())
            await self._shutdown.wait()
            await consumer.stop()
            try:
                await asyncio.wait_for(task, timeout=cfg.server.shutdown_grace_seconds)
            except TimeoutError:
                log.warning("consumer.shutdown_timeout")
                task.cancel()

        log.info("service.starting", environment=cfg.environment, version=cfg.service_version)
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(run_grpc(), name="grpc")
                tg.create_task(run_http(), name="http")
                tg.create_task(run_consumer(), name="consumer")
        except* Exception as group:
            for failure in group.exceptions:
                log.error("supervisor.task_failed", error=str(failure), exc_info=failure)
            raise
        finally:
            await set_serving(health_servicer, False)
            await grpc_server.stop(grace=cfg.server.shutdown_grace_seconds)
            await c.aclose()
            log.info("shutdown.complete")


async def serve() -> None:
    settings = get_settings()
    configure_logging(
        settings.observability,
        service=settings.service_name,
        version=settings.service_version,
    )
    configure_tracing(
        settings.observability,
        service=settings.service_name,
        version=settings.service_version,
    )
    await Supervisor(Container.build(settings)).run()
