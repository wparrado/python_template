"""Contract tests for IItemRepository.

Any implementation of IItemRepository must pass these tests.
Add new adapters to the `repository` fixture to validate them.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.domain.model.example.item import Item
from app.domain.ports.outbound.item_repository import IItemRepository
from app.domain.specifications.item_specifications import (
    ActiveItemSpecification,
    NameContainsSpecification,
    PriceInRangeSpecification,
)
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository


@pytest.fixture(params=["in_memory"])
def repository(request: pytest.FixtureRequest) -> IItemRepository:
    """Parametrized fixture: add new adapters here to run the full contract."""
    if request.param == "in_memory":
        return InMemoryItemRepository()
    raise ValueError(f"Unknown repository: {request.param}")


@pytest.mark.asyncio
async def test_save_and_find_by_id(repository: IItemRepository) -> None:
    item = Item.create(name="Widget", price=Decimal("9.99"))
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
    item1 = Item.create(name="A", price=Decimal("1.00"))
    item2 = Item.create(name="B", price=Decimal("2.00"))
    await repository.save(item1)
    await repository.save(item2)
    all_items = await repository.find_all()
    ids = {i.id for i in all_items}
    assert item1.id in ids
    assert item2.id in ids


@pytest.mark.asyncio
async def test_delete_removes_item(repository: IItemRepository) -> None:
    item = Item.create(name="ToDelete", price=Decimal("0.00"))
    await repository.save(item)
    await repository.delete(item.id)
    assert await repository.find_by_id(item.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_is_noop(repository: IItemRepository) -> None:
    """Deleting a non-existent item must not raise."""
    await repository.delete(uuid.uuid4())


@pytest.mark.asyncio
async def test_find_matching_by_name(repository: IItemRepository) -> None:
    gadget = Item.create(name="Super Gadget", price=Decimal("19.99"))
    widget = Item.create(name="Widget", price=Decimal("9.99"))
    await repository.save(gadget)
    await repository.save(widget)

    results = await repository.find_matching(NameContainsSpecification("gadget"))

    assert len(results) == 1
    assert results[0].id == gadget.id


@pytest.mark.asyncio
async def test_find_matching_by_price_range(repository: IItemRepository) -> None:
    cheap = Item.create(name="Cheap", price=Decimal("5.00"))
    expensive = Item.create(name="Expensive", price=Decimal("100.00"))
    await repository.save(cheap)
    await repository.save(expensive)

    results = await repository.find_matching(
        PriceInRangeSpecification(min_price=Decimal("1"), max_price=Decimal("10"))
    )

    assert len(results) == 1
    assert results[0].id == cheap.id


@pytest.mark.asyncio
async def test_find_matching_active_items(repository: IItemRepository) -> None:
    active = Item.create(name="Active", price=Decimal("1.00"))
    deleted = Item.create(name="Deleted", price=Decimal("2.00"))
    deleted.mark_deleted()
    await repository.save(active)
    await repository.save(deleted)

    results = await repository.find_matching(ActiveItemSpecification())

    ids = {i.id for i in results}
    assert active.id in ids
    assert deleted.id not in ids


@pytest.mark.asyncio
async def test_find_matching_composite_spec(repository: IItemRepository) -> None:
    match = Item.create(name="Blue Widget", price=Decimal("5.00"))
    no_match_name = Item.create(name="Red Widget", price=Decimal("5.00"))
    no_match_price = Item.create(name="Blue Widget", price=Decimal("50.00"))
    for item in (match, no_match_name, no_match_price):
        await repository.save(item)

    spec = NameContainsSpecification("blue") & PriceInRangeSpecification(max_price=Decimal("10"))
    results = await repository.find_matching(spec)

    assert len(results) == 1
    assert results[0].id == match.id
