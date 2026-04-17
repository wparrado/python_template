"""SystemClock — production implementation of IClock.

Returns the real current UTC time.  Inject this in the DI container for
all production code paths.
"""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Reads the current time from the OS clock."""

    def now(self) -> datetime:
        """Return the current UTC datetime."""
        return datetime.now(UTC)
