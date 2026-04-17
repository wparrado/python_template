"""Category aggregate root — example second bounded context.

Demonstrates how the hexagonal architecture scales when a second
independent aggregate is introduced alongside Item.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.domain.model.aggregate import AggregateRoot
from app.domain.model.example.category_events import (
    CategoryCreated,
    CategoryDeleted,
    CategoryUpdated,
)
from app.domain.model.example.category_value_objects import (
    CategoryDescription,
    CategoryName,
    CategorySlug,
)

if TYPE_CHECKING:
    from app.domain.ports.inbound.clock import IClock


@dataclass(kw_only=True)
class Category(AggregateRoot):
    """Category aggregate root.

    All state changes go through methods that enforce invariants
    (delegated to Value Objects) and emit domain events.

    ``slug`` is derived from ``name`` when not explicitly provided,
    ensuring every category has a URL-safe identifier from creation.
    ``kw_only=True`` lets these required VO fields coexist with the
    optional-with-defaults fields inherited from Entity / AggregateRoot.
    """

    name: CategoryName = field(default_factory=lambda: CategoryName("__unset__"))
    slug: CategorySlug = field(default_factory=lambda: CategorySlug("unset"))
    description: CategoryDescription = field(default_factory=CategoryDescription)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        slug: str | None = None,
        category_id: uuid.UUID | None = None,
        clock: IClock | None = None,
    ) -> Category:
        """Create a new Category.

        Accepts primitives for convenience; Value Objects are constructed
        internally and self-validate.  When *slug* is omitted it is derived
        automatically from *name*.

        When *clock* is provided its ``now()`` value is used for ``created_at``
        and ``updated_at``; otherwise falls back to ``datetime.now(UTC)``.
        """
        now = clock.now() if clock is not None else datetime.now(UTC)
        name_vo = CategoryName(name)
        slug_vo = CategorySlug(slug) if slug is not None else CategorySlug(name_vo.to_slug())
        category = cls(
            id=category_id or uuid.uuid4(),
            created_at=now,
            updated_at=now,
            name=name_vo,
            slug=slug_vo,
            description=CategoryDescription(description),
        )
        category._record_event(
            CategoryCreated(
                aggregate_id=category.id,
                name=category.name.value,
                slug=category.slug.value,
                description=category.description.value,
            )
        )
        return category

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def update(
        self,
        name: str | None = None,
        description: str | None = None,
        slug: str | None = None,
        *,
        clock: IClock,
    ) -> None:
        """Update category fields.

        Each assignment constructs a new Value Object, which self-validates.
        When *name* is updated and *slug* is not provided, the slug is
        re-derived from the new name.
        *clock* is required so that ``updated_at`` is deterministic.
        Pass a ``SystemClock`` in production or a ``FakeClock`` in tests.
        """
        if name is not None:
            self.name = CategoryName(name)
            if slug is None:
                self.slug = CategorySlug(self.name.to_slug())
        if slug is not None:
            self.slug = CategorySlug(slug)
        if description is not None:
            self.description = CategoryDescription(description)
        self._touch(clock=clock)
        self._record_event(
            CategoryUpdated(
                aggregate_id=self.id,
                name=name,
                slug=slug,
                description=description,
            )
        )

    def mark_deleted(self) -> None:
        """Mark this category as deleted and emit a CategoryDeleted event."""
        self.is_deleted = True
        self._record_event(CategoryDeleted(aggregate_id=self.id, category_id=self.id))
