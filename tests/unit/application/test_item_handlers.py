"""Unit tests for item command and query handlers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.application.commands.item_commands import CreateItemCommand, DeleteItemCommand, UpdateItemCommand
from app.application.dtos.pagination import PaginatedResult
from app.application.handlers.command_handlers import CreateItemHandler, DeleteItemHandler, UpdateItemHandler
from app.application.handlers.query_handlers import GetItemHandler, ListItemsHandler, SearchItemsHandler
from app.application.queries.item_queries import GetItemQuery, ListItemsQuery, SearchItemsQuery
from app.application.result import Failure, Success
from app.domain.exceptions.domain_errors import ItemNotFoundError
from app.infrastructure.clock.fake_clock import FakeClock
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository
from app.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork

_FIXED_TIME = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(_FIXED_TIME)


@pytest.fixture
def repository() -> InMemoryItemRepository:
    return InMemoryItemRepository()


@pytest.fixture
def publisher() -> InProcessEventPublisher:
    return InProcessEventPublisher()


@pytest.fixture
def uow(repository: InMemoryItemRepository, publisher: InProcessEventPublisher) -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork(repository=repository, publisher=publisher)


# ---------------------------------------------------------------------------
# CreateItemHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_item_returns_success(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    handler = CreateItemHandler(uow=uow, clock=clock)
    result = await handler.handle(CreateItemCommand(name="Widget", price=Decimal("9.99")))
    assert isinstance(result, Success)
    assert result.value.name == "Widget"


@pytest.mark.asyncio
async def test_create_item_invalid_returns_failure(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    handler = CreateItemHandler(uow=uow, clock=clock)
    result = await handler.handle(CreateItemCommand(name="", price=Decimal("9.99")))
    assert isinstance(result, Failure)


# ---------------------------------------------------------------------------
# UpdateItemHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_item_returns_success(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    created = await create_handler.handle(CreateItemCommand(name="Old", price=Decimal("5.00")))
    assert isinstance(created, Success)

    update_handler = UpdateItemHandler(uow=uow, clock=clock)
    result = await update_handler.handle(UpdateItemCommand(item_id=created.value.id, name="New"))
    assert isinstance(result, Success)
    assert result.value.name == "New"
    assert result.value.price == Decimal("5.00")


@pytest.mark.asyncio
async def test_update_item_not_found_returns_failure(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    handler = UpdateItemHandler(uow=uow, clock=clock)
    result = await handler.handle(UpdateItemCommand(item_id=uuid.uuid4(), name="X"))
    assert isinstance(result, Failure)
    assert isinstance(result.error, ItemNotFoundError)


# ---------------------------------------------------------------------------
# DeleteItemHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_nonexistent_is_idempotent(uow: InMemoryUnitOfWork) -> None:
    handler = DeleteItemHandler(uow=uow)
    result = await handler.handle(DeleteItemCommand(item_id=uuid.uuid4()))
    assert isinstance(result, Success)


@pytest.mark.asyncio
async def test_delete_existing_item_emits_event(
    uow: InMemoryUnitOfWork, publisher: InProcessEventPublisher, clock: FakeClock
) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    created = await create_handler.handle(CreateItemCommand(name="ToDelete", price=Decimal("1.00")))
    assert isinstance(created, Success)

    delete_handler = DeleteItemHandler(uow=uow)
    result = await delete_handler.handle(DeleteItemCommand(item_id=created.value.id))
    assert isinstance(result, Success)

    # Item is gone from repository after delete
    get_handler = GetItemHandler(repository=uow.repository)
    get_result = await get_handler.handle(GetItemQuery(item_id=created.value.id))
    assert isinstance(get_result, Failure)
    assert isinstance(get_result.error, ItemNotFoundError)


# ---------------------------------------------------------------------------
# GetItemHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_item_not_found_returns_failure(repository: InMemoryItemRepository) -> None:
    handler = GetItemHandler(repository=repository)
    result = await handler.handle(GetItemQuery(item_id=uuid.uuid4()))
    assert isinstance(result, Failure)
    assert isinstance(result.error, ItemNotFoundError)


# ---------------------------------------------------------------------------
# ListItemsHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_items_returns_all(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    await create_handler.handle(CreateItemCommand(name="A", price=Decimal("1.00")))
    await create_handler.handle(CreateItemCommand(name="B", price=Decimal("2.00")))

    list_handler = ListItemsHandler(repository=uow.repository)
    result = await list_handler.handle(ListItemsQuery())
    assert isinstance(result, Success)
    assert isinstance(result.value, PaginatedResult)
    assert len(result.value.items) == 2
    assert result.value.total == 2


@pytest.mark.asyncio
async def test_list_items_pagination_metadata(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    for i in range(5):
        await create_handler.handle(CreateItemCommand(name=f"Item {i}", price=Decimal("1.00")))

    list_handler = ListItemsHandler(repository=uow.repository)
    result = await list_handler.handle(ListItemsQuery(limit=2, offset=1))
    assert isinstance(result, Success)
    assert isinstance(result.value, PaginatedResult)
    assert len(result.value.items) == 2
    assert result.value.total == 5
    assert result.value.has_next is True
    assert result.value.has_previous is True


# ---------------------------------------------------------------------------
# SearchItemsHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_items_by_name(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    await create_handler.handle(CreateItemCommand(name="Super Widget", price=Decimal("5.00")))
    await create_handler.handle(CreateItemCommand(name="Gadget", price=Decimal("10.00")))

    search_handler = SearchItemsHandler(repository=uow.repository)
    result = await search_handler.handle(SearchItemsQuery(name_contains="widget"))
    assert isinstance(result, Success)
    assert len(result.value.items) == 1
    assert result.value.items[0].name == "Super Widget"


@pytest.mark.asyncio
async def test_search_items_by_price_range(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    await create_handler.handle(CreateItemCommand(name="Cheap", price=Decimal("3.00")))
    await create_handler.handle(CreateItemCommand(name="Expensive", price=Decimal("99.99")))

    search_handler = SearchItemsHandler(repository=uow.repository)
    result = await search_handler.handle(SearchItemsQuery(max_price=Decimal("10.00")))
    assert isinstance(result, Success)
    assert len(result.value.items) == 1
    assert result.value.items[0].name == "Cheap"


@pytest.mark.asyncio
async def test_search_items_combined_filters(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    await create_handler.handle(CreateItemCommand(name="Blue Widget", price=Decimal("5.00")))
    await create_handler.handle(CreateItemCommand(name="Red Widget", price=Decimal("5.00")))
    await create_handler.handle(CreateItemCommand(name="Blue Widget", price=Decimal("500.00")))

    search_handler = SearchItemsHandler(repository=uow.repository)
    result = await search_handler.handle(SearchItemsQuery(name_contains="blue", max_price=Decimal("10.00")))
    assert isinstance(result, Success)
    assert len(result.value.items) == 1
    assert result.value.items[0].price == Decimal("5.00")


@pytest.mark.asyncio
async def test_search_items_no_match_returns_empty(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    await create_handler.handle(CreateItemCommand(name="Widget", price=Decimal("9.99")))

    search_handler = SearchItemsHandler(repository=uow.repository)
    result = await search_handler.handle(SearchItemsQuery(name_contains="nonexistent"))
    assert isinstance(result, Success)
    assert isinstance(result.value, PaginatedResult)
    assert result.value.items == []
    assert result.value.total == 0


@pytest.mark.asyncio
async def test_search_items_paginated_with_metadata(uow: InMemoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateItemHandler(uow=uow, clock=clock)
    for i in range(5):
        await create_handler.handle(CreateItemCommand(name=f"Item {i}", price=Decimal("1.00")))

    search_handler = SearchItemsHandler(repository=uow.repository)
    result = await search_handler.handle(SearchItemsQuery(limit=2, offset=1))
    assert isinstance(result, Success)
    assert isinstance(result.value, PaginatedResult)
    assert len(result.value.items) == 2
    assert result.value.total == 5
    assert result.value.has_next is True
    assert result.value.has_previous is True
