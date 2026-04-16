"""Item query objects (CQRS — read side).

Queries express intent to read state without side effects.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

_DEFAULT_LIMIT = 50


@dataclass(frozen=True)
class GetItemQuery:
    """Query to retrieve a single item by its ID."""

    item_id: uuid.UUID
    query_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class ListItemsQuery:
    """Query to retrieve a paginated list of items."""

    limit: int = _DEFAULT_LIMIT
    offset: int = 0
    query_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class SearchItemsQuery:
    """Query to search items using composable domain specifications.

    All filter parameters are optional — omit them to match all items.
    Results are filtered by the active (non-deleted) status by default;
    set ``include_deleted=True`` to include soft-deleted items.
    """

    min_price: Decimal | None = None
    max_price: Decimal | None = None
    name_contains: str | None = None
    include_deleted: bool = False
    limit: int = _DEFAULT_LIMIT
    offset: int = 0
    query_id: uuid.UUID = field(default_factory=uuid.uuid4)
