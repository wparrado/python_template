"""Application settings driven entirely by environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic settings model — all values are read from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="app", description="Human-readable application name")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")

    # Authentication — Generic OIDC (works with Keycloak, Auth0, Cognito, Google, etc.)
    oidc_issuer: str = Field(default="", description="OIDC issuer URL, e.g. https://accounts.example.com")
    oidc_audience: str = Field(default="", description="Expected JWT audience claim")
    oidc_algorithms: list[str] = Field(default=["RS256"], description="Accepted JWT signing algorithms")

    # OpenTelemetry — any OTLP-compatible backend (Jaeger, Grafana Tempo, Datadog, …)
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP gRPC exporter endpoint",
    )
    otel_service_name: str = Field(default="app", description="Service name reported to OTEL backend")
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry instrumentation")

    # Rate limiting — backed by in-memory store in dev, Redis in prod
    rate_limit_enabled: bool = Field(default=True, description="Enable SlowAPI rate limiting")
    rate_limit_default: str = Field(default="100/minute", description="Default rate limit per endpoint")
    rate_limit_storage_uri: str = Field(
        default="memory://",
        description="Limits storage URI, e.g. 'redis://localhost:6379/0' for production",
    )

    # Circuit breaker — protects outbound HTTP calls (e.g. OIDC JWKS endpoint)
    cb_fail_max: int = Field(default=5, description="Consecutive failures before circuit opens")
    cb_reset_timeout: int = Field(default=60, description="Seconds before an open circuit moves to half-open")

    # Persistence backend
    db_backend: Literal["memory", "sqlalchemy"] = Field(
        default="memory",
        description="Persistence backend: 'memory' (default, no DB required) or 'sqlalchemy'",
    )
    database_url: str = Field(
        default="",
        description="SQLAlchemy async DB URL, e.g. postgresql+asyncpg://user:pass@host/db",
    )

    # Connection pool (only relevant when db_backend=sqlalchemy)
    db_pool_size: int = Field(
        default=10,
        description="Number of permanent connections kept in the pool",
    )
    db_max_overflow: int = Field(
        default=20,
        description="Extra connections allowed beyond pool_size (returned to pool when done)",
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Seconds to wait for a free connection before raising PoolTimeout",
    )
    db_pool_recycle: int = Field(
        default=1800,
        description="Max connection lifetime in seconds; prevents stale TCP connections",
    )
    db_pool_pre_ping: bool = Field(
        default=True,
        description="Emit a SELECT 1 before borrowing a connection to detect broken sockets",
    )

    # Transactional Outbox (only relevant when db_backend=sqlalchemy)
    outbox_poll_interval_seconds: float = Field(
        default=1.0,
        description="Seconds between OutboxRelay poll cycles",
    )

    # ── Message Broker ────────────────────────────────────────────────────────
    # The OutboxRelay forwards domain events to the configured downstream broker.
    # 'memory' (default) dispatches in-process only — no broker required.
    # 'rabbitmq' publishes to a topic exchange via aio-pika.
    # 'kafka' publishes to per-event topics via aiokafka.
    event_broker: Literal["memory", "rabbitmq", "kafka"] = Field(
        default="memory",
        description="Downstream event broker: 'memory', 'rabbitmq', or 'kafka'",
    )

    # RabbitMQ — required when event_broker='rabbitmq'
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost/",
        description="RabbitMQ AMQP URL, e.g. amqp://user:pass@host/vhost",
    )
    rabbitmq_exchange: str = Field(
        default="domain.events",
        description="RabbitMQ topic exchange where domain events are published",
    )

    # Kafka — required when event_broker='kafka'
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Comma-separated Kafka bootstrap servers",
    )
    kafka_topic_prefix: str = Field(
        default="app",
        description="Prefix prepended to event-type topics, e.g. 'app' → 'app.ItemCreated'",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
