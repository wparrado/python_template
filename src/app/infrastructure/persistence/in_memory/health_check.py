"""In-memory health check adapter.

Verifies that the in-memory repository is available (always true
for InMemory — the real value is establishing the pattern for
production adapters like SQLAlchemy that run a connectivity probe).
"""

from __future__ import annotations

from app.application.ports.health_check import HealthStatus, IHealthCheck
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository


class InMemoryRepositoryHealthCheck(IHealthCheck):
    """Health check that verifies the in-memory item repository is reachable."""

    def __init__(self, repository: InMemoryItemRepository) -> None:
        self._repository = repository

    async def check(self) -> HealthStatus:
        """Confirm the repository store is accessible."""
        try:
            await self._repository.count()
            return HealthStatus(name="in_memory_repository", healthy=True)
        except Exception as exc:  # noqa: BLE001
            return HealthStatus(name="in_memory_repository", healthy=False, detail=str(exc))
