"""Outbound port: IItemRepository.

This abstract interface is part of the domain layer.
Infrastructure adapters implement it.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.model.example.item import Item

_DEFAULT_LIMIT = 50


class IItemRepository(ABC):
    """Secondary (driven) port for item persistence."""

    @abstractmethod
    async def save(self, item: Item) -> None:
        """Persist a new or updated item."""

    @abstractmethod
    async def find_by_id(self, item_id: uuid.UUID) -> Item | None:
        """Return the item with the given id, or None if not found."""

    @abstractmethod
    async def find_all(self, limit: int = _DEFAULT_LIMIT, offset: int = 0) -> list[Item]:
        """Return items paginated by limit and offset."""

    @abstractmethod
    async def delete(self, item_id: uuid.UUID) -> None:
        """Delete the item with the given id (no-op if not found)."""
