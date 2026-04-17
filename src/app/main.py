"""FastAPI application factory.

Run with Granian:
    uv run granian --interface asgi app.main:app --host 0.0.0.0 --port 8000

Or via the project script:
    uv run serve
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.container import Container
from app.infrastructure.auth.oidc_verifier import OidcVerifier, make_current_user_dependency
from app.infrastructure.observability.logging import configure_logging
from app.infrastructure.observability.metrics import configure_metrics
from app.infrastructure.observability.tracing import configure_tracing
from app.infrastructure.rate_limiting.limiter import create_limiter
from app.presentation.api.v1.routers import categories, health, items
from app.presentation.app_state import AppState
from app.presentation.error_handlers import register_error_handlers
from app.presentation.middlewares.correlation_id import CorrelationIdMiddleware
from app.presentation.middlewares.telemetry_middleware import TelemetryMiddleware
from app.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    settings: Settings = fastapi_app.state.settings
    oidc_verifier: OidcVerifier = fastapi_app.state.oidc_verifier

    # Observability
    configure_logging(settings)
    configure_tracing(settings)
    configure_metrics(settings)

    # Auth
    await oidc_verifier.initialize()

    # Message broker — connect before the outbox relay starts dispatching
    broker = fastapi_app.state.broker
    if broker is not None:
        await broker.connect()

    # Outbox relay (only active when db_backend=sqlalchemy)
    relay = fastapi_app.state.outbox_relay
    if relay is not None:
        await relay.start()

    yield

    # Graceful shutdown — stop relay before disconnecting broker
    if relay is not None:
        await relay.stop()

    if broker is not None:
        await broker.disconnect()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory — testable and configurable."""
    if settings is None:
        settings = get_settings()

    fastapi_app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    container = Container(settings)
    oidc_verifier = OidcVerifier(settings, circuit_breaker=container.circuit_breaker())
    limiter = create_limiter(settings)

    # Attach limiter to app state so SlowAPI middleware can discover it
    fastapi_app.state.limiter = limiter

    # Single typed state object for presentation layer (application deps only)
    fastapi_app.state.app_state = AppState(
        item_service_dep=container.item_service_dependency(),
        category_service_dep=container.category_service_dependency(),
        get_current_user=make_current_user_dependency(oidc_verifier),
        health_checks=container.health_checks(),
    )
    # Infrastructure/settings stored separately for lifespan use
    fastapi_app.state.settings = settings
    fastapi_app.state.oidc_verifier = oidc_verifier
    fastapi_app.state.outbox_relay = container.outbox_relay()
    fastapi_app.state.broker = container.broker()

    # Middlewares (order matters: outermost first)
    fastapi_app.add_middleware(SlowAPIMiddleware)
    fastapi_app.add_middleware(TelemetryMiddleware)
    fastapi_app.add_middleware(CorrelationIdMiddleware)

    # OpenTelemetry auto-instrumentation
    FastAPIInstrumentor.instrument_app(fastapi_app)

    # Error handlers
    register_error_handlers(fastapi_app)
    fastapi_app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

    # Routers
    fastapi_app.include_router(health.router)
    fastapi_app.include_router(items.router, prefix="/api/v1")
    fastapi_app.include_router(categories.router, prefix="/api/v1")

    return fastapi_app


# Module-level app instance used by Granian
app = create_app()
