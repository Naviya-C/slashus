"""Typed, validated configuration. Fails at startup, not mid-batch."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The service root: <root>/src/<package>/config/settings.py -> parents[3].
# Resolved from the MODULE path, not the working directory, because
# ``env_file=".env"`` is CWD-relative -- running the CLI from src/ silently
# found no .env and every required field reported "Field required". The CWD
# entry is kept first so a local override still wins when you do run from the
# root.
_SERVICE_ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = (".env", _SERVICE_ROOT / ".env")


class _BaseConfig(BaseSettings):
    """Shared base so every settings group reads the same .env file.

    This is load-bearing, not cosmetic. Nested settings groups are created via
    ``default_factory``, and pydantic-settings builds each group's sources from
    ITS OWN ``model_config`` -- it does not inherit the parent's. Putting
    ``env_file`` only on the top-level ``Settings`` therefore meant every nested
    group read real OS environment variables but silently ignored ``.env``, so
    ``QDRANT_ENDPOINT=...`` in the file produced "Field required".
    """

    model_config = SettingsConfigDict(env_file=ENV_FILES, env_file_encoding="utf-8", extra="ignore")


class QdrantSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="QDRANT_",
        extra="ignore",
    )

    endpoint: str = Field(...)
    api_key: SecretStr | None = None
    collection: str = "sinhala_books_v5"
    timeout_seconds: int = Field(120, ge=1, le=600)
    dense_vector_name: str = "dense"
    sparse_vector_name: str = "sparse"

    @field_validator("endpoint")
    @classmethod
    def _scheme(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("QDRANT_ENDPOINT must start with http:// or https://")
        return v.rstrip("/")


class KafkaSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="KAFKA_",
        extra="ignore",
    )

    bootstrap_servers: str = "localhost:9092"
    group_id: str = "embedding-service"
    chunks_topic: str = "documents.chunks"
    dlq_topic: str = "documents.chunks.dlq"
    security_protocol: Literal["PLAINTEXT", "SSL", "SASL_SSL", "SASL_PLAINTEXT"] = "PLAINTEXT"
    sasl_mechanism: str | None = None
    sasl_username: str | None = None
    sasl_password: SecretStr | None = None
    batch_size: int = Field(32, ge=1, le=512)
    batch_timeout_seconds: float = Field(2.0, gt=0, le=60)
    max_poll_interval_ms: int = Field(600_000, ge=10_000)
    session_timeout_ms: int = Field(45_000, ge=6_000)
    # A batch failing this many times is dead-lettered. Without a ceiling a
    # single poison message halts its partition permanently while the topic
    # still looks healthy.
    max_batch_attempts: int = Field(3, ge=1, le=10)


class EmbeddingSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="EMBEDDING_",
        extra="ignore",
    )

    model_name: str = "BAAI/bge-m3"
    dimensions: int = Field(1024, ge=1)
    encode_batch_size: int = Field(16, ge=1, le=256)
    # ONNX Runtime thread count, set explicitly rather than letting the runtime
    # claim every core on a shared VM.
    onnx_threads: int = Field(2, ge=1, le=64)
    inference_workers: int = Field(2, ge=1, le=16)
    # int8: ~half the memory, faster CPU inference, small recall cost.
    quantized: bool = False
    # BGE-M3 takes no instruction prefix; kept configurable for other models.
    query_prefix: str = ""
    document_prefix: str = ""
    max_text_length: int = Field(8192, ge=64)


class SparseSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="SPARSE_",
        extra="ignore",
    )

    num_buckets: int = Field(1 << 20, ge=1 << 12, le=1 << 24)
    seed: int = 0
    min_token_length: int = Field(2, ge=1, le=8)
    tf_k1: float = Field(1.2, gt=0)


class RetrievalSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="RETRIEVAL_",
        extra="ignore",
    )

    # Server-side RRF fetches this many per leg before fusing. Fetching exactly
    # `limit` per leg hides two-leg consensus sitting just below the cutoff.
    oversample: float = Field(3.0, ge=1.0, le=10.0)
    title_scan_max_pages: int = Field(20, ge=1)
    title_scan_page_size: int = Field(1000, ge=1, le=10_000)
    title_cache_ttl_seconds: float = Field(300.0, ge=0)
    min_chunk_words: int = Field(8, ge=0)
    # Post-fusion near-duplicate removal. Textbook PDFs repeat headers across
    # pages, so an undiversified top-10 is often the same paragraph five times.
    diversity_threshold: float = Field(0.8, ge=0.0, le=1.0)
    title_confidence_threshold: float = Field(0.75, ge=0.0, le=1.0)
    title_weight: float = Field(0.8, gt=0.0, lt=1.0)
    global_weight: float = Field(0.2, gt=0.0, lt=1.0)

    @model_validator(mode="after")
    def _weights(self) -> RetrievalSettings:
        if abs(self.title_weight + self.global_weight - 1.0) > 1e-6:
            raise ValueError("RETRIEVAL_TITLE_WEIGHT + RETRIEVAL_GLOBAL_WEIGHT must equal 1")
        return self


class RedisSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="REDIS_",
        extra="ignore",
    )

    url: str | None = None


class ServerSettings(_BaseConfig):
    http_host: str = "0.0.0.0"
    http_port: int = Field(8004, ge=1, le=65535)
    grpc_host: str = "0.0.0.0"
    grpc_port: int = Field(50051, ge=1, le=65535)
    grpc_max_message_bytes: int = Field(16 * 1024 * 1024, ge=1024)
    grpc_max_concurrent_rpcs: int = Field(64, ge=1)
    grpc_tls_cert_file: str | None = None
    grpc_tls_key_file: str | None = None
    grpc_tls_client_ca_file: str | None = None
    service_token: SecretStr | None = Field(None, validation_alias="GRPC_SERVICE_TOKEN")
    shutdown_grace_seconds: float = Field(20.0, gt=0)

    @model_validator(mode="after")
    def _tls_pair(self) -> ServerSettings:
        if bool(self.grpc_tls_cert_file) != bool(self.grpc_tls_key_file):
            raise ValueError("GRPC_TLS_CERT_FILE and GRPC_TLS_KEY_FILE must be set together")
        return self

    @property
    def tls_enabled(self) -> bool:
        return bool(self.grpc_tls_cert_file and self.grpc_tls_key_file)


class ObservabilitySettings(_BaseConfig):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    otel_enabled: bool = False
    otel_endpoint: str | None = None
    metrics_enabled: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    environment: Literal["local", "staging", "production"] = "local"
    service_name: str = "embedding-service"
    service_version: str = "4.0.0"

    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)  # type: ignore[arg-type]
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    sparse: SparseSettings = Field(default_factory=SparseSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    @model_validator(mode="after")
    def _production(self) -> Settings:
        if self.environment == "production":
            if not self.qdrant.api_key:
                raise ValueError("QDRANT_API_KEY is required in production")
            if self.observability.log_format != "json":
                raise ValueError("production requires structured JSON logs")
            if not self.server.service_token and not self.server.grpc_tls_client_ca_file:
                raise ValueError("GRPC_SERVICE_TOKEN or mTLS client CA is required in production")
            if not self.redis.url:
                raise ValueError("REDIS_URL is required in production for cache invalidation")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
