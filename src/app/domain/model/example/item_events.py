"""Item domain events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.events.base import DomainEvent


@dataclass(frozen=True)
class ItemCreated(DomainEvent):
    name: str = ""
    price: float = 0.0
    description: str = ""


@dataclass(frozen=True)
class ItemUpdated(DomainEvent):
    name: str | None = None
    price: float | None = None
    description: str | None = None


@dataclass(frozen=True)
class ItemDeleted(DomainEvent):
    item_id: uuid.UUID = uuid.UUID(int=0)  # noqa: RUF009
