"""SQLAlchemy implementation of IItemRepository.

This is a secondary (driven) adapter.  It implements the domain outbound port
using an async SQLAlchemy session.  Domain model objects are never exposed
to SQLAlchemy — mapping is handled privately via ``_to_domain`` / ``_to_orm``.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func as sql_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants import DEFAULT_PAGE_SIZE
from app.domain.model.example.item import Item
from app.domain.model.example.value_objects import CategoryId, Description, ItemName, Money
from app.domain.ports.outbound.item_repository import IItemRepository
from app.domain.specifications.base import Specification
from app.infrastructure.persistence.sqlalchemy.models import ItemORM
from app.infrastructure.persistence.sqlalchemy.specification_translator import ItemSpecificationTranslator


class SQLAlchemyItemRepository(IItemRepository):
    """Async SQLAlchemy adapter for IItemRepository.

    Each instance wraps a single :class:`AsyncSession`.  The session lifecycle
    (begin / commit / rollback) is managed by :class:`SQLAlchemyUnitOfWork`.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an open async session."""
        self._session = session

    # ------------------------------------------------------------------
    # IItemRepository implementation
    # ------------------------------------------------------------------

    async def save(self, item: Item) -> None:
        """Persist a new or updated item (upsert via merge)."""
        orm = self._to_orm(item)
        await self._session.merge(orm)

    async def find_by_id(self, item_id: uuid.UUID) -> Item | None:
        """Return the active item with *item_id*, or ``None`` if not found or soft-deleted."""
        stmt = select(ItemORM).where(ItemORM.id == item_id, ItemORM.is_deleted == False)  # noqa: E712
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def find_all(self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> list[Item]:
        """Return active items paginated by *limit* and *offset*."""
        stmt = (
            select(ItemORM)
            .where(ItemORM.is_deleted == False)  # noqa: E712
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def find_matching(self, spec: Specification[Item]) -> list[Item]:
        """Return all items satisfying *spec* (translated to a SQL WHERE clause)."""
        clause = ItemSpecificationTranslator.translate(spec)
        stmt = select(ItemORM).where(clause)
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def delete(self, item_id: uuid.UUID) -> None:
        """Soft-delete the item by marking ``is_deleted = True``."""
        stmt = select(ItemORM).where(ItemORM.id == item_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            row.is_deleted = True

    async def count(self, spec: Specification[Item] | None = None) -> int:
        """Return total count matching *spec* (SQL WHERE clause), or all active items."""
        if spec is None:
            stmt = select(sql_func.count()).select_from(ItemORM).where(ItemORM.is_deleted == False)  # noqa: E712
        else:
            clause = ItemSpecificationTranslator.translate(spec)
            stmt = select(sql_func.count()).select_from(ItemORM).where(clause)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Private mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(orm: ItemORM) -> Item:
        """Map an :class:`ItemORM` row to an :class:`Item` domain object."""
        item = Item(
            id=orm.id,
            name=ItemName(orm.name),
            price=Money(Decimal(str(orm.price))),
            description=Description(orm.description),
            category_id=CategoryId(orm.category_id) if orm.category_id is not None else None,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
        item.is_deleted = orm.is_deleted
        return item

    @staticmethod
    def _to_orm(item: Item) -> ItemORM:
        """Map an :class:`Item` domain object to an :class:`ItemORM` row."""
        return ItemORM(
            id=item.id,
            name=item.name.value,
            price=item.price.amount,
            description=item.description.value,
            category_id=item.category_id.value if item.category_id is not None else None,
            is_deleted=item.is_deleted,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
