"""Item domain events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.domain.events.base import DomainEvent


@dataclass(frozen=True)
class ItemCreated(DomainEvent):
    """Emitted when a new item is successfully created."""

    name: str = ""
    price: Decimal = Decimal("0")  # noqa: RUF009
    description: str = ""


@dataclass(frozen=True)
class ItemUpdated(DomainEvent):
    """Emitted when an existing item's fields are updated."""

    name: str | None = None
    price: Decimal | None = None
    description: str | None = None


@dataclass(frozen=True)
class ItemDeleted(DomainEvent):
    """Emitted when an item is marked for deletion."""

    item_id: uuid.UUID = uuid.UUID(int=0)  # noqa: RUF009
