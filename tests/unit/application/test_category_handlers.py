"""Unit tests for category command and query handlers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.commands.category_commands import (
    CreateCategoryCommand,
    DeleteCategoryCommand,
    UpdateCategoryCommand,
)
from app.application.dtos.pagination import PaginatedResult
from app.application.handlers.category_command_handlers import (
    CreateCategoryHandler,
    DeleteCategoryHandler,
    UpdateCategoryHandler,
)
from app.application.handlers.category_query_handlers import (
    GetCategoryHandler,
    ListCategoriesHandler,
    SearchCategoriesHandler,
)
from app.application.queries.category_queries import (
    GetCategoryQuery,
    ListCategoriesQuery,
    SearchCategoriesQuery,
)
from app.application.result import Failure, Success
from app.domain.exceptions.domain_errors import CategoryNotFoundError
from app.infrastructure.clock.fake_clock import FakeClock
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.persistence.in_memory.category_repository import InMemoryCategoryRepository
from app.infrastructure.persistence.in_memory.category_unit_of_work import InMemoryCategoryUnitOfWork

_FIXED_TIME = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(_FIXED_TIME)


@pytest.fixture
def repository() -> InMemoryCategoryRepository:
    return InMemoryCategoryRepository()


@pytest.fixture
def publisher() -> InProcessEventPublisher:
    return InProcessEventPublisher()


@pytest.fixture
def uow(repository: InMemoryCategoryRepository, publisher: InProcessEventPublisher) -> InMemoryCategoryUnitOfWork:
    return InMemoryCategoryUnitOfWork(repository=repository, publisher=publisher)


# ---------------------------------------------------------------------------
# CreateCategoryHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_category_returns_success(uow: InMemoryCategoryUnitOfWork) -> None:
    handler = CreateCategoryHandler(uow=uow)
    result = await handler.handle(CreateCategoryCommand(name="Electronics"))
    assert isinstance(result, Success)
    assert result.value.name == "Electronics"
    assert result.value.slug == "electronics"


@pytest.mark.asyncio
async def test_create_category_with_explicit_slug(uow: InMemoryCategoryUnitOfWork) -> None:
    handler = CreateCategoryHandler(uow=uow)
    result = await handler.handle(CreateCategoryCommand(name="Electronics", slug="my-electronics"))
    assert isinstance(result, Success)
    assert result.value.slug == "my-electronics"


@pytest.mark.asyncio
async def test_create_category_invalid_returns_failure(uow: InMemoryCategoryUnitOfWork) -> None:
    handler = CreateCategoryHandler(uow=uow)
    result = await handler.handle(CreateCategoryCommand(name=""))
    assert isinstance(result, Failure)


@pytest.mark.asyncio
async def test_create_category_invalid_slug_returns_failure(uow: InMemoryCategoryUnitOfWork) -> None:
    handler = CreateCategoryHandler(uow=uow)
    result = await handler.handle(CreateCategoryCommand(name="Electronics", slug="INVALID SLUG"))
    assert isinstance(result, Failure)


# ---------------------------------------------------------------------------
# UpdateCategoryHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_category_returns_success(uow: InMemoryCategoryUnitOfWork, clock: FakeClock) -> None:
    create_handler = CreateCategoryHandler(uow=uow)
    created = await create_handler.handle(CreateCategoryCommand(name="Electronics"))
    assert isinstance(created, Success)

    update_handler = UpdateCategoryHandler(uow=uow, clock=clock)
    result = await update_handler.handle(
        UpdateCategoryCommand(category_id=created.value.id, name="Consumer Electronics")
    )
    assert isinstance(result, Success)
    assert result.value.name == "Consumer Electronics"
    assert result.value.slug == "consumer-electronics"


@pytest.mark.asyncio
async def test_update_category_not_found_returns_failure(uow: InMemoryCategoryUnitOfWork, clock: FakeClock) -> None:
    handler = UpdateCategoryHandler(uow=uow, clock=clock)
    result = await handler.handle(UpdateCategoryCommand(category_id=uuid.uuid4(), name="X"))
    assert isinstance(result, Failure)
    assert isinstance(result.error, CategoryNotFoundError)


# ---------------------------------------------------------------------------
# DeleteCategoryHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_nonexistent_is_idempotent(uow: InMemoryCategoryUnitOfWork) -> None:
    handler = DeleteCategoryHandler(uow=uow)
    result = await handler.handle(DeleteCategoryCommand(category_id=uuid.uuid4()))
    assert isinstance(result, Success)


@pytest.mark.asyncio
async def test_delete_existing_category(uow: InMemoryCategoryUnitOfWork, publisher: InProcessEventPublisher) -> None:
    create_handler = CreateCategoryHandler(uow=uow)
    created = await create_handler.handle(CreateCategoryCommand(name="ToDelete"))
    assert isinstance(created, Success)

    delete_handler = DeleteCategoryHandler(uow=uow)
    result = await delete_handler.handle(DeleteCategoryCommand(category_id=created.value.id))
    assert isinstance(result, Success)

    get_handler = GetCategoryHandler(repository=uow.repository)
    get_result = await get_handler.handle(GetCategoryQuery(category_id=created.value.id))
    assert isinstance(get_result, Failure)
    assert isinstance(get_result.error, CategoryNotFoundError)


# ---------------------------------------------------------------------------
# GetCategoryHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_category_not_found_returns_failure(repository: InMemoryCategoryRepository) -> None:
    handler = GetCategoryHandler(repository=repository)
    result = await handler.handle(GetCategoryQuery(category_id=uuid.uuid4()))
    assert isinstance(result, Failure)
    assert isinstance(result.error, CategoryNotFoundError)


# ---------------------------------------------------------------------------
# ListCategoriesHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_categories_returns_all(uow: InMemoryCategoryUnitOfWork) -> None:
    create_handler = CreateCategoryHandler(uow=uow)
    await create_handler.handle(CreateCategoryCommand(name="Electronics"))
    await create_handler.handle(CreateCategoryCommand(name="Books"))

    list_handler = ListCategoriesHandler(repository=uow.repository)
    result = await list_handler.handle(ListCategoriesQuery())
    assert isinstance(result, Success)
    assert isinstance(result.value, PaginatedResult)
    assert len(result.value.items) == 2
    assert result.value.total == 2


@pytest.mark.asyncio
async def test_list_categories_pagination_metadata(uow: InMemoryCategoryUnitOfWork) -> None:
    create_handler = CreateCategoryHandler(uow=uow)
    for i in range(5):
        await create_handler.handle(CreateCategoryCommand(name=f"Category {i}"))

    list_handler = ListCategoriesHandler(repository=uow.repository)
    result = await list_handler.handle(ListCategoriesQuery(limit=2, offset=1))
    assert isinstance(result, Success)
    assert isinstance(result.value, PaginatedResult)
    assert len(result.value.items) == 2
    assert result.value.total == 5
    assert result.value.has_next is True
    assert result.value.has_previous is True


# ---------------------------------------------------------------------------
# SearchCategoriesHandler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_categories_by_name(uow: InMemoryCategoryUnitOfWork) -> None:
    create_handler = CreateCategoryHandler(uow=uow)
    await create_handler.handle(CreateCategoryCommand(name="Electronics"))
    await create_handler.handle(CreateCategoryCommand(name="Books"))

    search_handler = SearchCategoriesHandler(repository=uow.repository)
    result = await search_handler.handle(SearchCategoriesQuery(name_contains="electro"))
    assert isinstance(result, Success)
    assert len(result.value.items) == 1
    assert result.value.items[0].name == "Electronics"


@pytest.mark.asyncio
async def test_search_categories_by_slug(uow: InMemoryCategoryUnitOfWork) -> None:
    create_handler = CreateCategoryHandler(uow=uow)
    await create_handler.handle(CreateCategoryCommand(name="Electronics"))
    await create_handler.handle(CreateCategoryCommand(name="Books"))

    search_handler = SearchCategoriesHandler(repository=uow.repository)
    result = await search_handler.handle(SearchCategoriesQuery(slug="books"))
    assert isinstance(result, Success)
    assert len(result.value.items) == 1
    assert result.value.items[0].slug == "books"


@pytest.mark.asyncio
async def test_search_categories_no_match_returns_empty(uow: InMemoryCategoryUnitOfWork) -> None:
    create_handler = CreateCategoryHandler(uow=uow)
    await create_handler.handle(CreateCategoryCommand(name="Electronics"))

    search_handler = SearchCategoriesHandler(repository=uow.repository)
    result = await search_handler.handle(SearchCategoriesQuery(name_contains="nonexistent"))
    assert isinstance(result, Success)
    assert isinstance(result.value, PaginatedResult)
    assert result.value.items == []
    assert result.value.total == 0


@pytest.mark.asyncio
async def test_search_categories_combined_filters(uow: InMemoryCategoryUnitOfWork) -> None:
    create_handler = CreateCategoryHandler(uow=uow)
    await create_handler.handle(CreateCategoryCommand(name="Blue Electronics"))
    await create_handler.handle(CreateCategoryCommand(name="Red Electronics"))
    await create_handler.handle(CreateCategoryCommand(name="Blue Books"))

    search_handler = SearchCategoriesHandler(repository=uow.repository)
    result = await search_handler.handle(SearchCategoriesQuery(name_contains="blue", slug="blue-electronics"))
    assert isinstance(result, Success)
    assert len(result.value.items) == 1
    assert result.value.items[0].name == "Blue Electronics"
