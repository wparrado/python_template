"""In-memory implementation of ICategoryRepository.

This is a secondary adapter (driven adapter).
It implements the domain's outbound port using a plain dict.
Swap this for SQLAlchemy, MongoDB, etc. by creating a new adapter
that implements ICategoryRepository — the domain never changes.
"""

from __future__ import annotations

import uuid

from app.application.constants import DEFAULT_PAGE_SIZE
from app.domain.model.example.category import Category
from app.domain.ports.outbound.category_repository import ICategoryRepository
from app.domain.specifications.base import Specification


class InMemoryCategoryRepository(ICategoryRepository):
    """Thread-unsafe in-memory repository suitable for testing and prototyping."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Category] = {}

    async def save(self, category: Category) -> None:
        self._store[category.id] = category

    async def find_by_id(self, category_id: uuid.UUID) -> Category | None:
        return self._store.get(category_id)

    async def find_by_slug(self, slug: str) -> Category | None:
        return next(
            (c for c in self._store.values() if c.slug.value == slug and not c.is_deleted),
            None,
        )

    async def find_all(self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> list[Category]:
        categories = list(self._store.values())
        return categories[offset : offset + limit]

    async def find_matching(self, spec: Specification[Category]) -> list[Category]:
        return [cat for cat in self._store.values() if spec.is_satisfied_by(cat)]

    async def delete(self, category_id: uuid.UUID) -> None:
        self._store.pop(category_id, None)

    async def count(self, spec: Specification[Category] | None = None) -> int:
        if spec is None:
            return len(self._store)
        return sum(1 for cat in self._store.values() if spec.is_satisfied_by(cat))
