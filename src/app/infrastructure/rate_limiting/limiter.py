"""Rate limiting factory.

Creates a configured SlowAPI Limiter instance that can be shared
across the application.  Storage defaults to in-memory (dev/test);
set ``RATE_LIMIT_STORAGE_URI=redis://...`` for production deployments.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import Settings


def create_limiter(settings: Settings) -> Limiter:
    """Return a SlowAPI Limiter configured from application settings."""
    return Limiter(
        key_func=get_remote_address,
        default_limits=[settings.rate_limit_default],
        storage_uri=settings.rate_limit_storage_uri,
        enabled=settings.rate_limit_enabled,
    )
