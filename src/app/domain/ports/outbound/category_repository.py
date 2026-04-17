"""Outbound port: ICategoryRepository.

This abstract interface is part of the domain layer.
Infrastructure adapters implement it.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.constants import DEFAULT_PAGE_SIZE
from app.domain.model.example.category import Category
from app.domain.specifications.base import Specification


class ICategoryRepository(ABC):
    """Secondary (driven) port for category persistence."""

    @abstractmethod
    async def save(self, category: Category) -> None:
        """Persist a new or updated category."""

    @abstractmethod
    async def find_by_id(self, category_id: uuid.UUID) -> Category | None:
        """Return the category with the given id, or None if not found."""

    @abstractmethod
    async def find_by_slug(self, slug: str) -> Category | None:
        """Return the category with the given slug, or None if not found."""

    @abstractmethod
    async def find_all(self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> list[Category]:
        """Return categories paginated by limit and offset."""

    @abstractmethod
    async def find_matching(self, spec: Specification[Category]) -> list[Category]:
        """Return all categories that satisfy *spec*."""

    @abstractmethod
    async def delete(self, category_id: uuid.UUID) -> None:
        """Delete the category with the given id (no-op if not found)."""

    @abstractmethod
    async def count(self, spec: Specification[Category] | None = None) -> int:
        """Return the total number of categories matching *spec*, or all if spec is None."""
