"""PaginatedResult — generic paginated response wrapper.

Used by query handlers to return both the data slice and the
metadata needed for client-side navigation (total count, cursors, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PaginatedResult(Generic[T]):
    """Immutable container for a paginated list of items plus navigation metadata.

    Attributes:
        items:  The data slice for the current page.
        total:  Total number of items matching the query (before pagination).
        limit:  Maximum number of items requested per page.
        offset: Number of items skipped before this page.
    """

    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_next(self) -> bool:
        """True when there are more items beyond the current page."""
        return self.offset + self.limit < self.total

    @property
    def has_previous(self) -> bool:
        """True when the current page is not the first."""
        return self.offset > 0
