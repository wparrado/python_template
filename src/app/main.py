"""FastAPI application factory.

Run with Granian:
    uv run granian --interface asgi app.main:app --host 0.0.0.0 --port 8000

Or via the project script:
    uv run serve
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.container import Container
from app.infrastructure.auth.oidc_verifier import OidcVerifier
from app.infrastructure.observability.logging import configure_logging
from app.infrastructure.observability.metrics import configure_metrics
from app.infrastructure.observability.tracing import configure_tracing
from app.presentation.api.v1.routers import health, items
from app.presentation.error_handlers import register_error_handlers
from app.presentation.middlewares.correlation_id import CorrelationIdMiddleware
from app.presentation.middlewares.telemetry_middleware import TelemetryMiddleware
from app.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    settings: Settings = app.state.settings

    # Observability
    configure_logging(settings)
    configure_tracing(settings)
    configure_metrics(settings)

    # Auth
    verifier: OidcVerifier = app.state.oidc_verifier
    await verifier.initialize()

    yield

    # Graceful shutdown (add cleanup here as needed)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory — testable and configurable."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # State
    app.state.settings = settings
    app.state.container = Container(settings)
    app.state.oidc_verifier = OidcVerifier(settings)

    # Middlewares (order matters: outermost first)
    app.add_middleware(TelemetryMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # OpenTelemetry auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)

    # Error handlers
    register_error_handlers(app)

    # Routers
    app.include_router(health.router)
    app.include_router(items.router, prefix="/api/v1")

    return app


# Module-level app instance used by Granian
app = create_app()
