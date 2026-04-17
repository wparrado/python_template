"""Outbound port: IHealthCheck.

Placed in the *application* layer because health verification is an
operational concern orchestrated by the application (not a business rule
of the domain).  The presentation layer lists registered checks via
``AppState``; infrastructure adapters implement this interface.

Port placement rationale
------------------------
* Domain layer  → pure business rules, no operational concerns.
* Application layer → orchestrates use-cases AND operational contracts
  (health, readiness) that cross the boundary between infra and presentation.
* Infrastructure → concrete adapters (SQLAlchemy probe, in-memory stub).
* Presentation  → consumes ``list[IHealthCheck]`` from ``AppState``
  without importing domain or infrastructure directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthStatus:
    """Result of a single infrastructure health check."""

    name: str
    healthy: bool
    detail: str = ""


class IHealthCheck(ABC):
    """Secondary (driven) port for infrastructure health verification.

    Each registered adapter implements ``check()`` and is aggregated by
    the readiness endpoint.  A single unhealthy result causes the probe
    to return HTTP 503.
    """

    @abstractmethod
    async def check(self) -> HealthStatus:
        """Run the health check and return its status."""
