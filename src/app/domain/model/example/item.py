"""Item aggregate root — example domain model.

Demonstrates: aggregate root, invariant enforcement,
domain event emission, factory methods.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.aggregate import AggregateRoot
from app.domain.model.example.item_events import ItemCreated, ItemDeleted, ItemUpdated


@dataclass
class Item(AggregateRoot):
    """Item aggregate root.

    All state changes go through methods that enforce invariants
    and emit domain events.
    """

    name: str = ""
    price: float = 0.0
    description: str = ""

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name: str,
        price: float,
        description: str = "",
        item_id: uuid.UUID | None = None,
    ) -> Item:
        """Create a new Item, enforcing invariants."""
        item = cls(
            id=item_id or uuid.uuid4(),
            name=name,
            price=price,
            description=description,
        )
        item._validate()
        item._record_event(
            ItemCreated(
                aggregate_id=item.id,
                name=item.name,
                price=item.price,
                description=item.description,
            )
        )
        return item

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def update(
        self,
        name: str | None = None,
        price: float | None = None,
        description: str | None = None,
    ) -> None:
        """Update item fields, enforcing invariants."""
        if name is not None:
            self.name = name
        if price is not None:
            self.price = price
        if description is not None:
            self.description = description
        self._validate()
        self._touch()
        self._record_event(
            ItemUpdated(
                aggregate_id=self.id,
                name=name,
                price=price,
                description=description,
            )
        )

    def mark_deleted(self) -> None:
        """Mark this item as deleted and emit an ItemDeleted event."""
        self._record_event(ItemDeleted(aggregate_id=self.id, item_id=self.id))

    # ------------------------------------------------------------------
    # Invariants
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("Item name must not be empty")
        if self.price < 0:
            raise ValidationError("Item price must be non-negative")
