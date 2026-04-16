"""Item query objects (CQRS — read side).

Queries express intent to read state without side effects.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GetItemQuery:
    item_id: uuid.UUID
    query_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class ListItemsQuery:
    query_id: uuid.UUID = field(default_factory=uuid.uuid4)
