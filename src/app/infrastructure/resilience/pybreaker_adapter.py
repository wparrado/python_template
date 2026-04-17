"""PyBreaker adapter for the ICircuitBreaker port.

Wraps a ``pybreaker.CircuitBreaker`` instance so it satisfies the
``ICircuitBreaker`` protocol.  All domain / infrastructure code depends
on the protocol — only this module imports pybreaker.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pybreaker

from app.settings import Settings


class PyBreakerAdapter:
    """Adapter that wraps pybreaker.CircuitBreaker to implement ICircuitBreaker."""

    def __init__(self, settings: Settings) -> None:
        self._breaker = pybreaker.CircuitBreaker(
            fail_max=settings.cb_fail_max,
            reset_timeout=settings.cb_reset_timeout,
            name="http_external",
        )

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *func* through the circuit breaker.

        Raises ``pybreaker.CircuitBreakerError`` when the circuit is open.
        """
        return self._breaker.call(func, *args, **kwargs)

    @property
    def current_state(self) -> str:
        """Return the current state: 'closed', 'open', or 'half_open'."""
        return self._breaker.current_state
