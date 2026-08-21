from __future__ import annotations

import json
import threading
from typing import Any

import structlog
from confluent_kafka import KafkaException, Producer

from ingestion_service.config import Settings
from ingestion_service.domain import (
    ChunkCreatedEvent,
    DocumentIngestedEvent,
    ImageEnrichmentRequested,
)

log = structlog.get_logger(__name__)

_google_credentials: Any | None = None
_google_credentials_lock = threading.Lock()


def _gcp_oauth_callback(_config: str | None = None) -> tuple[str, float]:
    """Return a short-lived ADC token in librdkafka's oauth_cb format."""
    global _google_credentials
    import google.auth
    from google.auth.transport.requests import Request

    with _google_credentials_lock:
        if _google_credentials is None:
            _google_credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        _google_credentials.refresh(Request())
        expiry = _google_credentials.expiry
        if not _google_credentials.token or expiry is None:
            raise RuntimeError("Google ADC did not return a token and expiry")
        return _google_credentials.token, expiry.timestamp()


def kafka_security(settings: Settings) -> dict[str, Any]:
    if settings.kafka_use_gcp_adc:
        return {
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "OAUTHBEARER",
            "oauth_cb": _gcp_oauth_callback,
        }
    config: dict[str, Any] = {"security.protocol": settings.kafka_security_protocol}
    if settings.kafka_sasl_mechanism:
        config["sasl.mechanism"] = settings.kafka_sasl_mechanism
    if settings.kafka_sasl_username:
        config["sasl.username"] = settings.kafka_sasl_username
    if settings.kafka_sasl_password:
        config["sasl.password"] = settings.kafka_sasl_password.get_secret_value()
    return config


class EventPublisher:
    def __init__(self, settings: Settings, producer: Producer | None = None) -> None:
        self._cfg = settings
        self._producer = producer or Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "enable.idempotence": True,
                "acks": "all",
                "compression.type": "zstd",
                "linger.ms": settings.kafka_linger_ms,
                "batch.num.messages": 10000,
                **kafka_security(settings),
            }
        )
        self._delivery_errors: list[str] = []

    def publish_chunk(self, event: ChunkCreatedEvent, *, partition_key: str) -> None:
        self._publish(self._cfg.kafka_chunks_topic, partition_key, event.wire_dict())

    def publish_image(self, event: ImageEnrichmentRequested) -> None:
        self._publish(self._cfg.kafka_image_topic, event.chunk_id, event.model_dump(mode="json"))

    def publish_completed(self, event: DocumentIngestedEvent) -> None:
        self._publish(
            self._cfg.kafka_completed_topic,
            event.doc_id,
            event.model_dump(mode="json"),
        )

    def publish_dlq(self, *, key: bytes | None, value: bytes, reason: str) -> None:
        self._publish_dlq(self._cfg.kafka_dlq_topic, key=key, value=value, reason=reason)

    def publish_image_dlq(self, *, key: bytes | None, value: bytes, reason: str) -> None:
        self._publish_dlq(self._cfg.kafka_image_dlq_topic, key=key, value=value, reason=reason)

    def _publish_dlq(self, topic: str, *, key: bytes | None, value: bytes, reason: str) -> None:
        self._producer.produce(
            topic,
            key=key,
            value=value,
            headers=[("dlq-reason", reason.encode("utf-8")[:1000])],
            on_delivery=self._delivery,
        )

    def _publish(self, topic: str, key: str, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        while True:
            try:
                self._producer.produce(
                    topic,
                    key=key.encode(),
                    value=encoded,
                    on_delivery=self._delivery,
                )
                break
            except BufferError:
                self._producer.poll(0.25)

    def _delivery(self, error, message) -> None:
        if error:
            self._delivery_errors.append(str(error))
            log.error("kafka.delivery_failed", topic=message.topic(), error=str(error))

    def poll(self) -> None:
        self._producer.poll(0)
        self._raise_delivery_errors()

    def flush_or_raise(self, timeout: float = 30.0) -> None:
        remaining = self._producer.flush(timeout)
        self._raise_delivery_errors()
        if remaining:
            raise KafkaException(f"{remaining} event(s) were not delivered before timeout")

    def _raise_delivery_errors(self) -> None:
        if self._delivery_errors:
            errors = "; ".join(self._delivery_errors[:5])
            self._delivery_errors.clear()
            raise KafkaException(errors)
