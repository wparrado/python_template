"""Category query objects (CQRS — read side).

Queries express intent to read state without side effects.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

_DEFAULT_LIMIT = 50


@dataclass(frozen=True)
class GetCategoryQuery:
    """Query to retrieve a single category by its ID."""

    category_id: uuid.UUID
    query_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class ListCategoriesQuery:
    """Query to retrieve a paginated list of categories."""

    limit: int = _DEFAULT_LIMIT
    offset: int = 0
    query_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class SearchCategoriesQuery:
    """Query to search categories using composable domain specifications.

    All filter parameters are optional — omit them to match all categories.
    Results are filtered by the active (non-deleted) status by default;
    set ``include_deleted=True`` to include soft-deleted categories.
    """

    name_contains: str | None = None
    slug: str | None = None
    include_deleted: bool = False
    limit: int = _DEFAULT_LIMIT
    offset: int = 0
    query_id: uuid.UUID = field(default_factory=uuid.uuid4)
