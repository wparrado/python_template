"""SQLAlchemy health check adapter.

Verifies database connectivity by executing a lightweight ``SELECT 1`` probe.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.application.ports.health_check import HealthStatus, IHealthCheck


class SQLAlchemyHealthCheck(IHealthCheck):
    """Health check that runs ``SELECT 1`` against the configured database."""

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialise with an async SQLAlchemy engine."""
        self._engine = engine

    async def check(self) -> HealthStatus:
        """Execute ``SELECT 1``; return healthy on success, unhealthy on failure."""
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return HealthStatus(name="postgresql", healthy=True)
        except SQLAlchemyError as exc:
            return HealthStatus(name="postgresql", healthy=False, detail=str(exc))
