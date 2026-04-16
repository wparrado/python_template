"""In-memory implementation of IItemRepository.

This is a secondary adapter (driven adapter).
It implements the domain's outbound port using a plain dict.
Swap this for SQLAlchemy, MongoDB, etc. by creating a new adapter
that implements IItemRepository — the domain never changes.

See persistence/README.md for how to add a real DB adapter.
"""

from __future__ import annotations

import uuid

from app.domain.model.example.item import Item
from app.domain.ports.outbound.item_repository import IItemRepository

_DEFAULT_LIMIT = 50


class InMemoryItemRepository(IItemRepository):
    """Thread-unsafe in-memory repository suitable for testing and prototyping."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Item] = {}

    async def save(self, item: Item) -> None:
        self._store[item.id] = item

    async def find_by_id(self, item_id: uuid.UUID) -> Item | None:
        return self._store.get(item_id)

    async def find_all(self, limit: int = _DEFAULT_LIMIT, offset: int = 0) -> list[Item]:
        items = list(self._store.values())
        return items[offset : offset + limit]

    async def delete(self, item_id: uuid.UUID) -> None:
        self._store.pop(item_id, None)
