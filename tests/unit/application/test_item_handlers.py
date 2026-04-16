"""Unit tests for item command and query handlers."""

from __future__ import annotations

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
    result = await handler.handle(CreateItemCommand(name="Widget", price=9.99))
    assert isinstance(result, Success)
    assert result.value.name == "Widget"


@pytest.mark.asyncio
async def test_create_item_invalid_returns_failure(
    repository: InMemoryItemRepository,
    publisher: InProcessEventPublisher,
) -> None:
    handler = CreateItemHandler(repository=repository, publisher=publisher)
    result = await handler.handle(CreateItemCommand(name="", price=9.99))
    assert isinstance(result, Failure)


@pytest.mark.asyncio
async def test_get_item_not_found_returns_failure(repository: InMemoryItemRepository) -> None:
    import uuid

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
    await create_handler.handle(CreateItemCommand(name="A", price=1.0))
    await create_handler.handle(CreateItemCommand(name="B", price=2.0))

    list_handler = ListItemsHandler(repository=repository)
    result = await list_handler.handle(ListItemsQuery())
    assert isinstance(result, Success)
    assert len(result.value) == 2


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_failure(
    repository: InMemoryItemRepository,
    publisher: InProcessEventPublisher,
) -> None:
    import uuid

    handler = DeleteItemHandler(repository=repository, publisher=publisher)
    result = await handler.handle(DeleteItemCommand(item_id=uuid.uuid4()))
    assert isinstance(result, Failure)
    assert isinstance(result.error, ItemNotFoundError)
