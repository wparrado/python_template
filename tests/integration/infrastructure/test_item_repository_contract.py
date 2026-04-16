"""Contract tests for IItemRepository.

Any implementation of IItemRepository must pass these tests.
Add new adapters to the `repository` fixture to validate them.
"""

from __future__ import annotations

import uuid

import pytest

from app.domain.model.example.item import Item
from app.domain.ports.outbound.item_repository import IItemRepository
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository


@pytest.fixture(params=["in_memory"])
def repository(request: pytest.FixtureRequest) -> IItemRepository:
    """Parametrized fixture: add new adapters here to run the full contract."""
    if request.param == "in_memory":
        return InMemoryItemRepository()
    raise ValueError(f"Unknown repository: {request.param}")


@pytest.mark.asyncio
async def test_save_and_find_by_id(repository: IItemRepository) -> None:
    item = Item.create(name="Widget", price=9.99)
    await repository.save(item)
    found = await repository.find_by_id(item.id)
    assert found is not None
    assert found.id == item.id
    assert found.name == "Widget"


@pytest.mark.asyncio
async def test_find_by_id_returns_none_for_missing(repository: IItemRepository) -> None:
    result = await repository.find_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_find_all_returns_all_items(repository: IItemRepository) -> None:
    item1 = Item.create(name="A", price=1.0)
    item2 = Item.create(name="B", price=2.0)
    await repository.save(item1)
    await repository.save(item2)
    all_items = await repository.find_all()
    ids = {i.id for i in all_items}
    assert item1.id in ids
    assert item2.id in ids


@pytest.mark.asyncio
async def test_delete_removes_item(repository: IItemRepository) -> None:
    item = Item.create(name="ToDelete", price=0.0)
    await repository.save(item)
    await repository.delete(item.id)
    assert await repository.find_by_id(item.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_is_noop(repository: IItemRepository) -> None:
    """Deleting a non-existent item must not raise."""
    await repository.delete(uuid.uuid4())
