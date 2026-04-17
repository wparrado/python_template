"""Outbound port: ICircuitBreaker.

Defines the contract that all circuit breaker implementations must satisfy.
The domain layer depends only on this Protocol — never on pybreaker directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable


class ICircuitBreaker(Protocol):
    """Structural protocol for a circuit breaker protecting outbound calls."""

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *func* through the circuit breaker.

        Raises ``CircuitBreakerError`` (or an application-level equivalent)
        when the circuit is open and calls are rejected.
        """
        raise NotImplementedError
