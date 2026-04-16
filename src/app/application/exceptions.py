"""Application-layer exception re-exports and wrappers.

These are the ONLY exception types the presentation layer should catch.
The application layer acts as a facade, re-exporting domain exceptions
so that the presentation layer never imports from the domain directly.
"""

from __future__ import annotations

from app.domain.exceptions.domain_errors import (
    ConflictError,
    DomainError,
    ItemNotFoundError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "ConflictError",
    "DomainError",
    "ItemNotFoundError",
    "NotFoundError",
    "ValidationError",
]
