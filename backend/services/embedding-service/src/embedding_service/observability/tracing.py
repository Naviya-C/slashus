"""OpenTelemetry setup. A no-op unless OTEL_ENABLED is set."""

from __future__ import annotations

import structlog

from embedding_service.config.settings import ObservabilitySettings

log = structlog.get_logger(__name__)


def configure_tracing(cfg: ObservabilitySettings, *, service: str, version: str) -> None:
    if not cfg.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service, "service.version": version})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=cfg.otel_endpoint))
        )
        trace.set_tracer_provider(provider)
        log.info("tracing.enabled", endpoint=cfg.otel_endpoint)
    except Exception:
        log.warning("tracing.setup_failed", exc_info=True)
