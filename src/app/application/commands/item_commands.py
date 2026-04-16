"""Item command objects (CQRS — write side).

Commands express intent to change state.
They carry all the data needed to execute the operation.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class CreateItemCommand:
    """Command to create a new item."""

    name: str
    price: Decimal
    description: str = ""
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class UpdateItemCommand:
    """Command to update an existing item (all fields optional)."""

    item_id: uuid.UUID
    name: str | None = None
    price: Decimal | None = None
    description: str | None = None
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class DeleteItemCommand:
    """Command to delete an item by ID."""

    item_id: uuid.UUID
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)
