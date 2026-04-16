"""Application settings driven entirely by environment variables."""

from functools import lru_cache

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
