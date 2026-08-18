"""Composition root and lifecycle.

Everything is built once at startup and injected. Lazy singletons built inside
request handlers race under concurrency: two simultaneous first requests each
see None and each construct a full dependency graph.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
from dataclasses import dataclass
from typing import Any

import structlog
import uvicorn
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agentic_service.adapters.llm import JsonLLM, build_model
from agentic_service.adapters.repository import SqlChatRepository
from agentic_service.adapters.vector_client import GrpcVectorClient
from agentic_service.agent.agent import build_agent
from agentic_service.agent.evaluator import AnswerEvaluator
from agentic_service.agent.runner import TurnRunner
from agentic_service.agent.tools import build_quiz_tools, build_tools
from agentic_service.api.server import create_app
from agentic_service.cache.semantic import SemanticCache
from agentic_service.config.settings import Settings, get_settings
from agentic_service.memory.manager import MemoryManager
from agentic_service.memory.repository import SqlMemoryRepository
from agentic_service.memory.store import build_store
from agentic_service.observability.health import ComponentState, HealthRegistry
from agentic_service.observability.logging import configure_logging
from agentic_service.observability.tracing import configure_tracing
from agentic_service.prompts.pool import get_prompt_pool

log = structlog.get_logger(__name__)
 

@dataclass
class Container:
    settings: Settings
    health: HealthRegistry
    vectors: GrpcVectorClient
    repository: SqlChatRepository
    memory: MemoryManager
    evaluator: AnswerEvaluator
    store: Any
    cache: SemanticCache
    runner: TurnRunner
    engine: Any
    redis: Any = None
    _store_manager: Any = None

    async def aclose(self) -> None:
        with contextlib.suppress(Exception):
            await self.runner.drain()
        with contextlib.suppress(Exception):
            await self.vectors.close()
        if self._store_manager is not None:
            with contextlib.suppress(Exception):
                await self._store_manager.__aexit__(None, None, None)
        if self.redis is not None:
            with contextlib.suppress(Exception):
                await self.redis.aclose()
        with contextlib.suppress(Exception):
            await self.engine.dispose()


async def build_container(settings: Settings) -> Container:
    health = HealthRegistry()
    for component in ("database", "vector-search", "llm", "prompts", "memory-store"):
        health.register(component, required=component != "memory-store")

    prompts = get_prompt_pool()
    health.set("prompts", ComponentState.HEALTHY, f"{len(prompts.names())} templates")

    engine = create_async_engine(
        settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_recycle=settings.database.pool_recycle_seconds,
        pool_pre_ping=True,
        echo=settings.database.echo,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repository = SqlChatRepository(session_factory)

    redis_client = None
    if settings.redis.url:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.redis.url,
            decode_responses=True,
            max_connections=settings.redis.max_connections,
        )

    vectors = GrpcVectorClient(settings.vector)

    store, store_manager = await build_store(
        redis_url=settings.redis.url,
        vectors=vectors,
        dimensions=settings.memory.embed_dimensions,
    )
    health.set(
        "memory-store",
        ComponentState.HEALTHY if store_manager else ComponentState.DEGRADED,
        "redis" if store_manager else "in-process",
    )

    model = build_model(settings.llm)
    json_llm = JsonLLM(model)

    checkpointer = None
    if redis_client is not None:
        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver

            saver = AsyncRedisSaver(settings.redis.url)
            await saver.asetup()
            checkpointer = saver
            log.info("checkpointer.redis")
        except Exception:
            log.warning("checkpointer.redis_failed", exc_info=True)
    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver

        log.warning("checkpointer.in_memory", detail="working memory will not survive restart")
        checkpointer = MemorySaver()

    cache = SemanticCache(
        redis=redis_client,
        vectors=vectors,
        threshold=settings.cache.similarity_threshold,
        ttl_seconds=settings.cache.ttl_seconds,
        max_entries_per_scope=settings.cache.max_entries_per_scope,
        enabled=settings.cache.enabled,
    )
    memory = MemoryManager(
        SqlMemoryRepository(session_factory),
        vectors=vectors,
        llm=json_llm,
        on_change=cache.invalidate_memory,
    )
    evaluator = AnswerEvaluator(json_llm)
    tools = [
        *build_tools(vectors, memory),
        *build_quiz_tools(repository, evaluator),
    ]
    agent = build_agent(
        model=model,
        tools=tools,
        memory=memory,
        store=store,
        checkpointer=checkpointer,
        settings=settings.agent,
        base_prompt=prompts.render("SYSTEM"),
    )

    runner = TurnRunner(
        agent=agent,
        memory=memory,
        settings=settings.agent,
        cache=cache,
        consolidation_enabled=settings.memory.consolidation_enabled,
    )

    return Container(
        settings=settings,
        health=health,
        vectors=vectors,
        repository=repository,
        memory=memory,
        evaluator=evaluator,
        store=store,
        cache=cache,
        runner=runner,
        engine=engine,
        redis=redis_client,
        _store_manager=store_manager,
    )


async def probe(container: Container) -> None:
    health = container.health
    health.set(
        "database",
        ComponentState.HEALTHY if await container.repository.healthy() else ComponentState.DEGRADED,
    )
    health.set(
        "vector-search",
        ComponentState.HEALTHY if await container.vectors.healthy() else ComponentState.DEGRADED,
    )

    health.set("llm", ComponentState.HEALTHY, container.settings.llm.model)


async def serve() -> None:
    settings = get_settings()
    configure_logging(
        settings.observability, service=settings.service_name, version=settings.service_version
    )
    configure_tracing(
        settings.observability, service=settings.service_name, version=settings.service_version
    )

    container = await build_container(settings)
    await probe(container)

    app = create_app(settings=settings, container=container, health=container.health)
    shutdown = asyncio.Event()

    loop = asyncio.get_running_loop()

    def _signal(sig: signal.Signals) -> None:
        log.info("shutdown.signal", signal=sig.name)
        container.health.begin_shutdown()
        shutdown.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal, sig)

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=settings.http_host,
            port=settings.http_port,
            log_config=None,
            access_log=False,
            timeout_graceful_shutdown=int(settings.shutdown_grace_seconds),
        )
    )
    server.install_signal_handlers = lambda: None  # type: ignore[method-assign]

    async def health_loop() -> None:
        while not shutdown.is_set():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(shutdown.wait(), timeout=30)
            if not shutdown.is_set():
                await probe(container)

    log.info("service.starting", environment=settings.environment, port=settings.http_port)
    probe_task = asyncio.create_task(health_loop())
    try:
        await server.serve()
    finally:
        shutdown.set()
        probe_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await probe_task
        await container.aclose()
        log.info("shutdown.complete")
