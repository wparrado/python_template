"""ResilienceContainer — owns circuit breaker and resilience adapters.

Isolates all fault-tolerance infrastructure so the root Container does
not import pybreaker or any resilience library directly.
"""

from __future__ import annotations

from app.domain.ports.outbound.circuit_breaker import ICircuitBreaker
from app.infrastructure.resilience.pybreaker_adapter import PyBreakerAdapter
from app.settings import Settings


class ResilienceContainer:
    """Manages resilience adapters (circuit breaker, etc.).

    Constructed once and shared for the lifetime of the process.
    """

    def __init__(self, settings: Settings) -> None:
        self._circuit_breaker: ICircuitBreaker = PyBreakerAdapter(settings)

    def circuit_breaker(self) -> ICircuitBreaker:
        """Return the shared circuit breaker adapter."""
        return self._circuit_breaker
