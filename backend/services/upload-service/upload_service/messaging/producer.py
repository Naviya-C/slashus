"""
upload_service/messaging/producer.py
====================================

Emits DocUploaded to the `doc.uploaded` topic after the PDF is safely in storage.
"""

from __future__ import annotations

import json
import logging
import os

from confluent_kafka import Producer

from contracts import DocUploaded

log = logging.getLogger(__name__)


class UploadPublisher:
    def __init__(self, *, bootstrap: str, topic: str):
        self._topic = topic
        self._p = Producer({
            "bootstrap.servers": bootstrap,
            "enable.idempotence": True,
            "linger.ms": 20,
        })
        log.info("kafka producer ready: topic=%s bootstrap=%s", self._topic, bootstrap)

    @classmethod
    def from_env(cls) -> "UploadPublisher":
        return cls(
            bootstrap=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            topic=os.getenv("UPLOAD_TOPIC", "documents.uploaded"),
        )

    def publish(self, evt: DocUploaded) -> None:
        payload = json.dumps(evt.to_dict(), ensure_ascii=False).encode("utf-8")
        
        log.info("Publishing to topic=%s", self._topic)
        log.info("Payload=%s", payload.decode("utf-8"))
        
        self._p.produce(self._topic, key=evt.doc_id.encode("utf-8"),
                        value=payload, on_delivery=self._ack)
        self._p.poll(0)

    def flush(self, timeout: float = 15.0) -> None:
        remaining = self._p.flush(timeout)
        if remaining:
            log.error("%d upload event(s) not delivered before timeout", remaining)

    @staticmethod
    def _ack(err, msg):
        if err:
            log.error("upload event publish failed: %s", err)
        else:
            log.info(
                "upload event delivered: topic=%s partition=%d offset=%d",
                msg.topic(),
                msg.partition(),
                msg.offset(),
            )
