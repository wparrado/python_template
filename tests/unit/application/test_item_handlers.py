"""Unit tests for item command and query handlers."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.application.commands.item_commands import CreateItemCommand, DeleteItemCommand
from app.application.handlers.command_handlers import CreateItemHandler, DeleteItemHandler
from app.application.handlers.query_handlers import GetItemHandler, ListItemsHandler
from app.application.queries.item_queries import GetItemQuery, ListItemsQuery
from app.application.result import Failure, Success
from app.domain.exceptions.domain_errors import ItemNotFoundError
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository


@pytest.fixture
def repository() -> InMemoryItemRepository:
    return InMemoryItemRepository()


@pytest.fixture
def publisher() -> InProcessEventPublisher:
    return InProcessEventPublisher()


@pytest.mark.asyncio
async def test_create_item_returns_success(
    repository: InMemoryItemRepository,
    publisher: InProcessEventPublisher,
) -> None:
    handler = CreateItemHandler(repository=repository, publisher=publisher)
    result = await handler.handle(CreateItemCommand(name="Widget", price=Decimal("9.99")))
    assert isinstance(result, Success)
    assert result.value.name == "Widget"


@pytest.mark.asyncio
async def test_create_item_invalid_returns_failure(
    repository: InMemoryItemRepository,
    publisher: InProcessEventPublisher,
) -> None:
    handler = CreateItemHandler(repository=repository, publisher=publisher)
    result = await handler.handle(CreateItemCommand(name="", price=Decimal("9.99")))
    assert isinstance(result, Failure)


@pytest.mark.asyncio
async def test_get_item_not_found_returns_failure(repository: InMemoryItemRepository) -> None:
    handler = GetItemHandler(repository=repository)
    result = await handler.handle(GetItemQuery(item_id=uuid.uuid4()))
    assert isinstance(result, Failure)
    assert isinstance(result.error, ItemNotFoundError)


@pytest.mark.asyncio
async def test_list_items_returns_all(
    repository: InMemoryItemRepository,
    publisher: InProcessEventPublisher,
) -> None:
    create_handler = CreateItemHandler(repository=repository, publisher=publisher)
    await create_handler.handle(CreateItemCommand(name="A", price=Decimal("1.00")))
    await create_handler.handle(CreateItemCommand(name="B", price=Decimal("2.00")))

    list_handler = ListItemsHandler(repository=repository)
    result = await list_handler.handle(ListItemsQuery())
    assert isinstance(result, Success)
    assert len(result.value) == 2


@pytest.mark.asyncio
async def test_list_items_pagination(
    repository: InMemoryItemRepository,
    publisher: InProcessEventPublisher,
) -> None:
    create_handler = CreateItemHandler(repository=repository, publisher=publisher)
    for i in range(5):
        await create_handler.handle(CreateItemCommand(name=f"Item {i}", price=Decimal("1.00")))

    list_handler = ListItemsHandler(repository=repository)
    result = await list_handler.handle(ListItemsQuery(limit=2, offset=1))
    assert isinstance(result, Success)
    assert len(result.value) == 2


@pytest.mark.asyncio
async def test_delete_nonexistent_is_idempotent(
    repository: InMemoryItemRepository,
    publisher: InProcessEventPublisher,
) -> None:
    handler = DeleteItemHandler(repository=repository, publisher=publisher)
    result = await handler.handle(DeleteItemCommand(item_id=uuid.uuid4()))
    assert isinstance(result, Success)
