"""Domain inbound port: IClock.

Abstracts the system clock so that aggregates and domain services can
obtain the current time without depending on ``datetime.now()`` directly.

Why this belongs here
---------------------
``datetime.now(UTC)`` is an *external* dependency — it calls the OS clock,
which is outside the domain's control.  Wrapping it behind a Protocol lets
infrastructure provide the real implementation (``SystemClock``) while tests
inject a deterministic one (``FakeClock``), making time-sensitive invariants
fully testable without monkey-patching or freezegun.

Usage in aggregates
-------------------
Aggregates accept ``clock: IClock | None = None`` in their factory and
mutation methods.  When ``None`` is passed (the default) they fall back to
``datetime.now(UTC)`` so existing call-sites require no changes::

    item = Item.create(name="Widget", price=Decimal("9.99"))           # uses system clock
    item = Item.create(name="Widget", price=Decimal("9.99"), clock=c)  # uses injected clock

Implementations
---------------
* ``app.infrastructure.clock.system_clock.SystemClock`` — production adapter.
* ``app.infrastructure.clock.fake_clock.FakeClock``     — test helper.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class IClock(Protocol):
    """Read-only view of the current time.

    Implementations must return timezone-aware datetimes (UTC recommended).
    """

    def now(self) -> datetime:
        """Return the current date and time."""
        ...
