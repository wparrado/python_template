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
from app.domain.specifications.base import Specification

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

    async def find_matching(self, spec: Specification[Item]) -> list[Item]:
        return [item for item in self._store.values() if spec.is_satisfied_by(item)]

    async def delete(self, item_id: uuid.UUID) -> None:
        self._store.pop(item_id, None)
