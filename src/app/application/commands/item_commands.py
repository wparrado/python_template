"""Item command objects (CQRS — write side).

Commands express intent to change state.
They carry all the data needed to execute the operation.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Final

# Sentinel distinguishing "caller passed None (clear category)" from "omitted".
CATEGORY_ID_UNSET: Final[object] = object()


@dataclass(frozen=True)
class CreateItemCommand:
    """Command to create a new item."""

    name: str
    price: Decimal
    description: str = ""
    category_id: uuid.UUID | None = None
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class UpdateItemCommand:
    """Command to update an existing item (all fields optional).

    ``category_id=None`` explicitly removes the category association.
    Omitting ``category_id`` (default ``CATEGORY_ID_UNSET``) leaves it unchanged.
    """

    item_id: uuid.UUID
    name: str | None = None
    price: Decimal | None = None
    description: str | None = None
    category_id: uuid.UUID | None | object = field(default_factory=lambda: CATEGORY_ID_UNSET)
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class DeleteItemCommand:
    """Command to delete an item by ID."""

    item_id: uuid.UUID
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)
