"""Item aggregate root — example domain model.

Demonstrates: aggregate root, invariant enforcement via Value Objects,
domain event emission, factory methods.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.domain.model.aggregate import AggregateRoot
from app.domain.model.example.item_events import ItemCreated, ItemDeleted, ItemUpdated
from app.domain.model.example.value_objects import CategoryId, Description, ItemName, Money

if TYPE_CHECKING:
    from app.domain.ports.inbound.clock import IClock


@dataclass(kw_only=True)
class Item(AggregateRoot):
    """Item aggregate root.

    All state changes go through methods that enforce invariants
    (delegated to Value Objects) and emit domain events.

    Fields use Value Objects so that invariants are enforced at
    construction time — no separate _validate() step is needed.
    ``kw_only=True`` lets these required VO fields coexist with the
    optional-with-defaults fields inherited from Entity / AggregateRoot.
    """

    name: ItemName = field(default_factory=lambda: ItemName("__unset__"))
    price: Money = field(default_factory=lambda: Money(Decimal("0")))
    description: Description = field(default_factory=Description)
    category_id: CategoryId | None = field(default=None)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name: str,
        price: Decimal,
        description: str = "",
        item_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        clock: IClock | None = None,
    ) -> Item:
        """Create a new Item.

        Accepts primitives for convenience; Value Objects are constructed
        internally and self-validate, so no separate _validate() call is needed.

        When *clock* is provided its ``now()`` value is used for ``created_at``
        and ``updated_at``; otherwise falls back to ``datetime.now(UTC)``.
        """
        now = clock.now() if clock is not None else datetime.now(UTC)
        item = cls(
            id=item_id or uuid.uuid4(),
            created_at=now,
            updated_at=now,
            name=ItemName(name),
            price=Money(price),
            description=Description(description),
            category_id=CategoryId(category_id) if category_id is not None else None,
        )
        item._record_event(
            ItemCreated(
                aggregate_id=item.id,
                name=item.name.value,
                price=item.price.amount,
                description=item.description.value,
            )
        )
        return item

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def update(
        self,
        name: str | None = None,
        price: Decimal | None = None,
        description: str | None = None,
        category_id: uuid.UUID | None = None,
        *,
        update_category: bool = False,
        clock: IClock,
    ) -> None:
        """Update item fields.

        Each assignment constructs a new Value Object, which self-validates.
        *clock* is required so that ``updated_at`` is deterministic.
        Pass a ``SystemClock`` in production or a ``FakeClock`` in tests.

        Pass ``category_id=None`` together with ``update_category=True`` to
        explicitly remove the category association.  Omit ``update_category``
        (default ``False``) to leave ``category_id`` unchanged.
        """
        if name is not None:
            self.name = ItemName(name)
        if price is not None:
            self.price = Money(price)
        if description is not None:
            self.description = Description(description)
        if update_category:
            self.category_id = CategoryId(category_id) if category_id is not None else None
        self._touch(clock=clock)
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
        self.is_deleted = True
        self._record_event(ItemDeleted(aggregate_id=self.id, item_id=self.id))
