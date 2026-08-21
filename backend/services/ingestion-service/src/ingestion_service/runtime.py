from __future__ import annotations

import threading
from dataclasses import dataclass

from redis import Redis

from ingestion_service.api import create_app
from ingestion_service.config import Settings
from ingestion_service.documents import (
    CSVReader,
    DOCXReader,
    HTMLReader,
    ImageReader,
    JSONReader,
    PDFReader,
    PPTXReader,
    ReaderRegistry,
    TextReader,
    XLSXReader,
)
from ingestion_service.documents.ocr import OCREngine
from ingestion_service.documents.piliwela_adapter import PiliwelaConverter
from ingestion_service.messaging import DocumentConsumer, EventPublisher
from ingestion_service.observability import HealthRegistry
from ingestion_service.pipeline import IngestionService, JobRepository
from ingestion_service.storage import create_stores
from ingestion_service.vision import DistributedVisionGuard, GeminiCaptioner, VisionWorker


@dataclass
class Runtime:
    app: object
    worker: DocumentConsumer | VisionWorker
    health: HealthRegistry

    def start_worker(self) -> threading.Thread:
        thread = threading.Thread(target=self.worker.run, name="ingestion-worker", daemon=False)
        thread.start()
        return thread

    def stop(self, thread: threading.Thread) -> None:
        self.health.shutting_down = True
        self.worker.stop()
        thread.join(timeout=20)


def build_ingestion_runtime(settings: Settings) -> Runtime:
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    redis.ping()
    jobs = JobRepository(redis, ttl_seconds=settings.job_ttl_seconds)
    health = HealthRegistry()
    source, assets = create_stores(settings)
    ocr = (
        OCREngine(
            languages=settings.ocr_languages,
            dpi=settings.ocr_dpi,
            timeout_seconds=settings.ocr_timeout_seconds,
        )
        if settings.ocr_enabled
        else None
    )
    registry = ReaderRegistry(
        [
            PDFReader(settings=settings, ocr=ocr, converter=PiliwelaConverter()),
            DOCXReader(),
            PPTXReader(),
            XLSXReader(),
            ImageReader(ocr),
            HTMLReader(),
            CSVReader(),
            JSONReader(),
            TextReader(),
        ]
    )
    publisher = EventPublisher(settings)
    service = IngestionService(
        settings=settings,
        source_store=source,
        asset_store=assets,
        readers=registry,
        publisher=publisher,
        jobs=jobs,
    )
    consumer = DocumentConsumer(
        settings=settings,
        service=service,
        jobs=jobs,
        publisher=publisher,
        health=health,
    )
    return Runtime(app=create_app(health=health, jobs=jobs), worker=consumer, health=health)


def build_vision_runtime(settings: Settings) -> Runtime:
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    redis.ping()
    jobs = JobRepository(redis, ttl_seconds=settings.job_ttl_seconds)
    health = HealthRegistry()
    _, assets = create_stores(settings)
    publisher = EventPublisher(settings)
    worker = VisionWorker(
        settings=settings,
        store=assets,
        captioner=GeminiCaptioner(settings),
        guard=DistributedVisionGuard(
            redis,
            requests_per_minute=settings.vision_requests_per_minute,
            circuit_seconds=settings.vision_circuit_seconds,
        ),
        publisher=publisher,
        health=health,
    )
    return Runtime(app=create_app(health=health, jobs=jobs), worker=worker, health=health)
