"""Unit tests for the resilience infrastructure layer.

Covers PyBreakerAdapter: circuit breaker state transitions
(closed → open → half-open) and call execution.
"""

from __future__ import annotations

import pytest
import pybreaker

from app.infrastructure.resilience.pybreaker_adapter import PyBreakerAdapter
from app.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_name="test",
        oidc_issuer="",
        otel_enabled=False,
        cb_fail_max=3,
        cb_reset_timeout=60,
    )


@pytest.fixture
def adapter(settings: Settings) -> PyBreakerAdapter:
    return PyBreakerAdapter(settings)


# ---------------------------------------------------------------------------
# Normal execution
# ---------------------------------------------------------------------------


def test_initial_state_is_closed(adapter: PyBreakerAdapter) -> None:
    assert adapter.current_state == "closed"


def test_call_executes_function(adapter: PyBreakerAdapter) -> None:
    result = adapter.call(lambda: 42)
    assert result == 42


def test_call_passes_args_and_kwargs(adapter: PyBreakerAdapter) -> None:
    def add(a: int, b: int = 0) -> int:
        return a + b

    assert adapter.call(add, 3, b=4) == 7


def test_call_propagates_exception(adapter: PyBreakerAdapter) -> None:
    def boom() -> None:
        raise ValueError("expected error")

    with pytest.raises(ValueError, match="expected error"):
        adapter.call(boom)


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


def test_circuit_opens_after_fail_max(adapter: PyBreakerAdapter) -> None:
    def fail() -> None:
        raise Exception("failure")

    for _ in range(3):
        try:
            adapter.call(fail)
        except Exception:
            pass

    assert adapter.current_state == "open"


def test_open_circuit_raises_circuit_breaker_error(adapter: PyBreakerAdapter) -> None:
    def fail() -> None:
        raise Exception("failure")

    for _ in range(3):
        try:
            adapter.call(fail)
        except Exception:
            pass

    with pytest.raises(pybreaker.CircuitBreakerError):
        adapter.call(lambda: "should not reach")


def test_successful_calls_do_not_open_circuit(adapter: PyBreakerAdapter) -> None:
    for _ in range(10):
        adapter.call(lambda: "ok")
    assert adapter.current_state == "closed"


def test_circuit_resets_on_success_after_failures(adapter: PyBreakerAdapter) -> None:
    fail_count = 0

    def sometimes_fail() -> str:
        nonlocal fail_count
        if fail_count < 2:
            fail_count += 1
            raise Exception("transient")
        return "ok"

    for _ in range(2):
        try:
            adapter.call(sometimes_fail)
        except Exception:
            pass

    assert adapter.current_state == "closed"
    result = adapter.call(sometimes_fail)
    assert result == "ok"
