from __future__ import annotations

from datetime import UTC, datetime

from redis import Redis

from ingestion_service.domain import DocumentUploadedEvent, JobState, JobStatus


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class JobRepository:
    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    @staticmethod
    def _key(job_id: str) -> str:
        return f"ingestion:job:{job_id}"

    def begin_attempt(self, event: DocumentUploadedEvent) -> JobState:
        key = self._key(event.effective_job_id)
        attempts = int(self._redis.hincrby(key, "attempts", 1))
        now = utc_now()
        mapping = {
            "job_id": event.effective_job_id,
            "doc_id": event.doc_id,
            "user_id": event.user_id,
            "source_name": event.source_name,
            "status": JobStatus.DOWNLOADING.value,
            "attempts": attempts,
            "started_at": now,
            "updated_at": now,
            "error": "",
        }
        self._redis.hset(key, mapping=mapping)
        self._redis.expire(key, self._ttl)
        return self.get(event.effective_job_id)  # type: ignore[return-value]

    def progress(
        self,
        job_id: str,
        *,
        units_processed: int,
        chunks_published: int,
        images_queued: int,
    ) -> None:
        self._redis.hset(
            self._key(job_id),
            mapping={
                "status": JobStatus.PARTIALLY_SEARCHABLE.value,
                "units_processed": units_processed,
                "chunks_published": chunks_published,
                "images_queued": images_queued,
                "updated_at": utc_now(),
            },
        )

    def complete(self, job_id: str) -> None:
        now = utc_now()
        self._redis.hset(
            self._key(job_id),
            mapping={
                "status": JobStatus.COMPLETED.value,
                "updated_at": now,
                "completed_at": now,
            },
        )

    def fail(self, job_id: str, error: str) -> None:
        self._redis.hset(
            self._key(job_id),
            mapping={
                "status": JobStatus.FAILED.value,
                "error": error[:1000],
                "updated_at": utc_now(),
            },
        )

    def get(self, job_id: str) -> JobState | None:
        raw = self._redis.hgetall(self._key(job_id))
        if not raw:
            return None
        decoded = {
            (key.decode() if isinstance(key, bytes) else key): (
                value.decode() if isinstance(value, bytes) else value
            )
            for key, value in raw.items()
        }
        optional_ints = {"units_total"}
        ints = {"units_processed", "chunks_published", "images_queued", "attempts"}
        for field in ints:
            decoded[field] = int(decoded.get(field) or 0)
        for field in optional_ints:
            decoded[field] = int(decoded[field]) if decoded.get(field) else None
        for field in ("error", "started_at", "completed_at"):
            decoded[field] = decoded.get(field) or None
        return JobState.model_validate(decoded)
