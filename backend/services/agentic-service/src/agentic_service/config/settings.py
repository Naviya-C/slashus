"""Typed configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_SERVICE_ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = (".env", _SERVICE_ROOT / ".env")


class _BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, env_file_encoding="utf-8", extra="ignore")


class LLMSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.6-plus"
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(2048, ge=64, le=32_000)
    request_timeout_seconds: float = Field(90.0, gt=0, le=600)
    max_retries: int = Field(2, ge=0, le=5)


class AgentSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="AGENT_",
        extra="ignore",
    )


    recursion_limit: int = Field(25, ge=4, le=100)
    max_tool_calls: int = Field(10, ge=1, le=50)
    turn_timeout_seconds: float = Field(180.0, gt=0, le=900)
    max_window_tokens: int = Field(6000, ge=500, le=200_000)
    keep_recent_messages: int = Field(12, ge=2, le=200)
    summarization_enabled: bool = True
    stream_tokens: bool = True


class MemorySettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="MEMORY_",
        extra="ignore",
    )

    embed_dimensions: int = Field(1024, ge=8)
    consolidation_enabled: bool = True


class CacheSettings(_BaseConfig):
    """Semantic response cache."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="CACHE_",
        extra="ignore",
    )

    enabled: bool = True
    similarity_threshold: float = Field(0.95, ge=0.5, le=1.0)
    ttl_seconds: int = Field(86_400, ge=60)
    max_entries_per_scope: int = Field(200, ge=10, le=5000)


class DatabaseSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="DATABASE_",
        extra="ignore",
    )

    url: str = Field(...)
    pool_size: int = Field(10, ge=1, le=100)
    max_overflow: int = Field(5, ge=0, le=100)
    pool_recycle_seconds: int = Field(1800, ge=60)
    echo: bool = False

    @field_validator("url")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not v.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            raise ValueError("DATABASE_URL must use an async driver")
        return v


class RedisSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="REDIS_",
        extra="ignore",
    )

    url: str | None = None
    max_connections: int = Field(20, ge=1)


class VectorSettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="EMBEDDING_",
        extra="ignore",
    )

    grpc_url: str = "embedding-service:50051"
    search_timeout_seconds: float = Field(30.0, gt=0)
    titles_timeout_seconds: float = Field(15.0, gt=0)
    tls_enabled: bool = False
    tls_ca_file: str | None = None
    service_token: SecretStr | None = None


class SecuritySettings(_BaseConfig):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_prefix="SECURITY_",
        extra="ignore",
    )

    gateway_shared_secret: SecretStr | None = None
    rate_limit_per_minute: int = Field(30, ge=1, le=1000)
    cors_allow_origins: list[str] = Field(default_factory=list)


class ObservabilitySettings(_BaseConfig):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    metrics_enabled: bool = True
    otel_enabled: bool = False
    otel_endpoint: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    environment: Literal["local", "staging", "production"] = "local"
    service_name: str = "agentic-service"
    service_version: str = "4.0.0"
    http_host: str = "0.0.0.0"
    http_port: int = Field(8084, ge=1, le=65535)
    shutdown_grace_seconds: float = Field(20.0, gt=0)

    llm: LLMSettings = Field(default_factory=LLMSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore[arg-type]
    redis: RedisSettings = Field(default_factory=RedisSettings)
    vector: VectorSettings = Field(default_factory=VectorSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    @model_validator(mode="after")
    def _production_guardrails(self) -> Settings:
        if self.memory.embed_dimensions != 1024:
            raise ValueError("MEMORY_EMBED_DIMENSIONS must be 1024 to match the pgvector migration")
        if self.environment == "production":
            if not self.llm.api_key:
                raise ValueError("LLM_API_KEY is required in production")
            if not self.redis.url:
                raise ValueError("REDIS_URL is required in production")
            if not self.security.gateway_shared_secret:
                raise ValueError("SECURITY_GATEWAY_SHARED_SECRET is required in production")
            if not self.vector.service_token and not self.vector.tls_enabled:
                raise ValueError("EMBEDDING_SERVICE_TOKEN or gRPC TLS is required in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
