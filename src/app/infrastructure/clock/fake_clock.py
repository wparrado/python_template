"""FakeClock — deterministic IClock implementation for tests.

Provides full control over the current time so that time-sensitive domain
invariants (e.g. ``updated_at`` changed after an update, expiry windows)
can be tested without relying on the real wall clock or external patching
libraries.

Usage::

    from datetime import UTC, datetime, timedelta
    from app.infrastructure.clock.fake_clock import FakeClock

    fixed = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    clock = FakeClock(fixed)

    item = Item.create(name="Widget", price=Decimal("9.99"), clock=clock)
    assert item.created_at == fixed

    clock.tick(timedelta(hours=1))
    item.update(name="Updated", clock=clock)
    assert item.updated_at == fixed + timedelta(hours=1)
"""

from __future__ import annotations

from datetime import datetime, timedelta


class FakeClock:
    """Deterministic clock for tests.

    Starts at ``fixed_time`` and advances only when ``tick()`` is called.
    """

    def __init__(self, fixed_time: datetime) -> None:
        """Initialise the clock at ``fixed_time`` (must be timezone-aware)."""
        if fixed_time.tzinfo is None:
            raise ValueError("FakeClock requires a timezone-aware datetime.")
        self._current = fixed_time

    def now(self) -> datetime:
        """Return the current frozen time."""
        return self._current

    def tick(self, delta: timedelta) -> None:
        """Advance the clock by ``delta``."""
        self._current += delta
