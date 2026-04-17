"""SQLAlchemy implementation of ICategoryRepository.

This is a secondary (driven) adapter.  It implements the domain outbound port
using an async SQLAlchemy session.  Domain model objects are never exposed
to SQLAlchemy — mapping is handled privately via ``_to_domain`` / ``_to_orm``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import false, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from app.application.constants import DEFAULT_PAGE_SIZE
from app.domain.model.example.category import Category
from app.domain.model.example.category_value_objects import (
    CategoryDescription,
    CategoryName,
    CategorySlug,
)
from app.domain.ports.outbound.category_repository import ICategoryRepository
from app.domain.specifications.base import Specification
from app.infrastructure.persistence.sqlalchemy.models import CategoryORM
from app.infrastructure.persistence.sqlalchemy.specification_translator_category import (
    CategorySpecificationTranslator,
)


class SQLAlchemyCategoryRepository(ICategoryRepository):
    """Async SQLAlchemy adapter for ICategoryRepository.

    Each instance wraps a single :class:`AsyncSession`.  The session lifecycle
    (begin / commit / rollback) is managed by :class:`SQLAlchemyCategoryUnitOfWork`.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an open async session."""
        self._session = session

    # ------------------------------------------------------------------
    # ICategoryRepository implementation
    # ------------------------------------------------------------------

    async def save(self, category: Category) -> None:
        """Persist a new or updated category (upsert via merge)."""
        orm = self._to_orm(category)
        await self._session.merge(orm)

    async def find_by_id(self, category_id: uuid.UUID) -> Category | None:
        """Return the active category with *category_id*, or ``None`` if not found or soft-deleted."""
        stmt = select(CategoryORM).where(
            CategoryORM.id == category_id, CategoryORM.is_deleted == false()
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def find_by_slug(self, slug: str) -> Category | None:
        """Return the active category with *slug*, or ``None`` if not found or soft-deleted."""
        stmt = select(CategoryORM).where(
            CategoryORM.slug == slug, CategoryORM.is_deleted == false()
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def find_all(self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> list[Category]:
        """Return active categories paginated by *limit* and *offset*."""
        stmt = (
            select(CategoryORM)
            .where(CategoryORM.is_deleted == false())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def find_matching(self, spec: Specification[Category]) -> list[Category]:
        """Return all categories satisfying *spec* (translated to a SQL WHERE clause)."""
        clause = CategorySpecificationTranslator.translate(spec)
        stmt = select(CategoryORM).where(clause)
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def delete(self, category_id: uuid.UUID) -> None:
        """Soft-delete the category by marking ``is_deleted = True``."""
        stmt = select(CategoryORM).where(CategoryORM.id == category_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            row.is_deleted = True

    async def count(self, spec: Specification[Category] | None = None) -> int:
        """Return total count matching *spec* (SQL WHERE clause), or all active categories."""
        if spec is None:
            stmt = (
                select(sql_count())
                .select_from(CategoryORM)
                .where(CategoryORM.is_deleted == false())
            )
        else:
            clause = CategorySpecificationTranslator.translate(spec)
            stmt = select(sql_count()).select_from(CategoryORM).where(clause)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Private mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(orm: CategoryORM) -> Category:
        """Map a :class:`CategoryORM` row to a :class:`Category` domain object."""
        category = Category(
            id=orm.id,
            name=CategoryName(orm.name),
            slug=CategorySlug(orm.slug),
            description=CategoryDescription(orm.description),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
        category.is_deleted = orm.is_deleted
        return category

    @staticmethod
    def _to_orm(category: Category) -> CategoryORM:
        """Map a :class:`Category` domain object to a :class:`CategoryORM` row."""
        return CategoryORM(
            id=category.id,
            name=category.name.value,
            slug=category.slug.value,
            description=category.description.value,
            is_deleted=category.is_deleted,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )
