from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env",), extra="ignore")

    service_host: str = "0.0.0.0"
    service_port: int = Field(8003, ge=1, le=65535)
    log_level: str = "INFO"

    storage_backend: str = "gcs"
    local_storage_root: str = "/tmp/slashus-storage"
    source_bucket: str = "slashus-source-documents"
    asset_bucket: str = "slashus-document-assets"
    storage_prefix: str = ""

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_upload_topic: str = "documents.uploaded"
    kafka_chunks_topic: str = "documents.chunks"
    kafka_image_topic: str = "documents.images"
    kafka_completed_topic: str = "documents.ingested"
    kafka_dlq_topic: str = "documents.uploaded.dlq"
    kafka_image_dlq_topic: str = "documents.images.dlq"
    kafka_group_id: str = "ingestion-service"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_use_gcp_adc: bool = False
    kafka_sasl_mechanism: str | None = None
    kafka_sasl_username: str | None = None
    kafka_sasl_password: SecretStr | None = None
    kafka_max_poll_interval_ms: int = Field(1_800_000, ge=60_000)
    kafka_max_document_attempts: int = Field(3, ge=1, le=10)
    kafka_linger_ms: int = Field(25, ge=0, le=1000)

    redis_url: str = "redis://localhost:6379/0"
    job_ttl_seconds: int = Field(604_800, ge=3600)

    chunk_max_tokens: int = Field(720, ge=64, le=4096)
    chunk_overlap_tokens: int = Field(80, ge=0, le=512)
    max_document_bytes: int = Field(200 * 1024 * 1024, ge=1024)
    max_document_units: int = Field(2000, ge=1)

    ocr_enabled: bool = True
    ocr_languages: str = "eng+sin"
    ocr_dpi: int = Field(200, ge=72, le=400)
    ocr_timeout_seconds: int = Field(45, ge=1, le=300)
    ocr_min_text_characters: int = Field(80, ge=0)

    heading_max_characters: int = Field(180, ge=20, le=500)
    heading_h1_ratio: float = Field(1.50, ge=1.1, le=3.0)
    heading_h2_ratio: float = Field(1.28, ge=1.05, le=2.5)
    heading_h3_ratio: float = Field(1.10, ge=1.0, le=2.0)

    extract_images: bool = True
    min_image_width: int = Field(120, ge=1)
    min_image_height: int = Field(120, ge=1)
    min_image_area_ratio: float = Field(0.02, ge=0, le=1)
    max_images_per_unit: int = Field(8, ge=0, le=100)

    vision_enrichment_enabled: bool = False
    vision_model: str = "gemini-2.5-flash"
    vision_requests_per_minute: int = Field(10, ge=1)
    vision_max_attempts: int = Field(3, ge=1, le=10)
    vision_circuit_seconds: int = Field(90, ge=1)
    gemini_api_key: SecretStr | None = None

    @field_validator("storage_prefix")
    @classmethod
    def clean_prefix(cls, value: str) -> str:
        return value.strip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
