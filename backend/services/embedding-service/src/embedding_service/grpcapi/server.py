"""
gRPC server assembly.

Adds four things:

  * STANDARD HEALTH. `grpc.health.v1.Health`.
  * REFLECTION. Without it `grpcurl` cannot introspect the service, so
    debugging a live instance means writing a client first.
  * INTERCEPTORS. Logging, metrics, and a correlation id on every call, in one
    place instead of repeated per handler.
  * TLS. The old server bound `add_insecure_port` unconditionally. Optional
    server TLS with optional client-cert verification is available here for
    anything crossing a trust boundary.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import grpc
import inspect
import structlog
from grpc.aio import ServerInterceptor
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from embedding_service.config.settings import ServerSettings
from embedding_service.observability.metrics import GRPC_DURATION, GRPC_REQUESTS
from embedding_service.proto_gen import search_pb2, search_pb2_grpc

log = structlog.get_logger(__name__)

SERVICE_NAME = "slashus.search.v2.VectorSearch"


class ObservabilityInterceptor(ServerInterceptor):
    """Correlation id, structured access log, and RPC metrics."""

    async def intercept_service(
        self,
        continuation: Callable[[Any], Awaitable[Any]],
        handler_call_details: Any,
    ) -> Any:
        method = (handler_call_details.method or "unknown").rsplit("/", 1)[-1]
        metadata = dict(handler_call_details.invocation_metadata or ())
        correlation_id = metadata.get("x-correlation-id") or str(uuid.uuid4())

        handler = await continuation(handler_call_details)
        if handler is None or handler.unary_unary is None:
            return handler

        inner = handler.unary_unary

        async def wrapper(request: Any, context: grpc.aio.ServicerContext) -> Any:
            structlog.contextvars.bind_contextvars(correlation_id=correlation_id, rpc=method)
            started = time.perf_counter()
            code = "OK"
            try:
                result = inner(request, context)
                if inspect.isawaitable(result):
                    return await result
                return result 
            except grpc.aio.AbortError:
                code = str(context.code().name if context.code() else "ABORTED")
                raise
            except Exception:
                code = "INTERNAL"
                log.error("grpc.unhandled", rpc=method, exc_info=True)
                raise
            finally:
                elapsed = time.perf_counter() - started
                GRPC_DURATION.labels(method=method).observe(elapsed)
                GRPC_REQUESTS.labels(method=method, code=code).inc()
                log.info("grpc.request", rpc=method, code=code, ms=round(elapsed * 1000, 1))
                structlog.contextvars.unbind_contextvars("correlation_id", "rpc")

        return grpc.unary_unary_rpc_method_handler(
            wrapper,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )


def _credentials(cfg: ServerSettings) -> grpc.ServerCredentials:
    with open(cfg.grpc_tls_key_file, "rb") as f:  # type: ignore[arg-type]
        key = f.read()
    with open(cfg.grpc_tls_cert_file, "rb") as f:  # type: ignore[arg-type]
        cert = f.read()

    root: bytes | None = None
    if cfg.grpc_tls_client_ca_file:
        with open(cfg.grpc_tls_client_ca_file, "rb") as f:
            root = f.read()

    return grpc.ssl_server_credentials(
        [(key, cert)],
        root_certificates=root,
        require_client_auth=root is not None,
    )


async def build_server(
    servicer: search_pb2_grpc.VectorSearchServicer, cfg: ServerSettings
) -> tuple[grpc.aio.Server, health.HealthServicer]:
    server = grpc.aio.server(
        interceptors=[ObservabilityInterceptor()],
        maximum_concurrent_rpcs=cfg.grpc_max_concurrent_rpcs,
        options=[
            ("grpc.max_send_message_length", cfg.grpc_max_message_bytes),
            ("grpc.max_receive_message_length", cfg.grpc_max_message_bytes),
            ("grpc.keepalive_time_ms", 30_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.min_ping_interval_without_data_ms", 10_000),
        ],
    )

    search_pb2_grpc.add_VectorSearchServicer_to_server(servicer, server)

    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set(SERVICE_NAME, health_pb2.HealthCheckResponse.NOT_SERVING)
    health_servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)

    reflection.enable_server_reflection(
        (
            search_pb2.DESCRIPTOR.services_by_name["VectorSearch"].full_name,
            health_pb2.DESCRIPTOR.services_by_name["Health"].full_name,
            reflection.SERVICE_NAME,
        ),
        server,
    )

    address = f"{cfg.grpc_host}:{cfg.grpc_port}"
    if cfg.tls_enabled:
        server.add_secure_port(address, _credentials(cfg))
        log.info("grpc.tls_enabled", mutual=bool(cfg.grpc_tls_client_ca_file))
    else:
        server.add_insecure_port(address)

    log.info("grpc.configured", address=address, tls=cfg.tls_enabled)
    return server, health_servicer


def set_serving(health_servicer: health.HealthServicer, serving: bool) -> None:
    status = (
        health_pb2.HealthCheckResponse.SERVING
        if serving
        else health_pb2.HealthCheckResponse.NOT_SERVING
    )
    health_servicer.set(SERVICE_NAME, status)
    health_servicer.set("", status)
