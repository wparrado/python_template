"""Application-wide constants.

Re-exports domain pagination constants so that the application and
presentation layers can import from a single, stable path without
creating circular or cross-layer dependencies.
"""

from __future__ import annotations

from app.domain.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

__all__ = ["DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE"]
