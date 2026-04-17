"""Category domain events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.events.base import DomainEvent


@dataclass(frozen=True)
class CategoryCreated(DomainEvent):
    """Emitted when a new category is successfully created."""

    name: str = ""
    slug: str = ""
    description: str = ""


@dataclass(frozen=True)
class CategoryUpdated(DomainEvent):
    """Emitted when an existing category's fields are updated."""

    name: str | None = None
    slug: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class CategoryDeleted(DomainEvent):
    """Emitted when a category is marked for deletion."""

    category_id: uuid.UUID = uuid.UUID(int=0)  # noqa: RUF009
