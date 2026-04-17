"""CategoryApplicationService — concrete implementation of the inbound port.

Orchestrates command and query handlers, translates Result values into
either a return value or a raised domain exception, and exposes a clean
async interface to the presentation layer.

The service is the boundary between presentation and application:
  - Presentation calls the ICategoryApplicationService Protocol.
  - This class fulfils that Protocol.
  - Domain errors propagate as exceptions; the presentation layer maps
    them to HTTP responses via the registered error handlers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.application.commands.category_commands import (
    CreateCategoryCommand,
    DeleteCategoryCommand,
    UpdateCategoryCommand,
)
from app.application.constants import DEFAULT_PAGE_SIZE
from app.application.dtos.category_dtos import CategoryOutputDTO, CategorySearchParams
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
from app.application.ports.category_application_service import ICategoryApplicationService
from app.application.queries.category_queries import (
    GetCategoryQuery,
    ListCategoriesQuery,
    SearchCategoriesQuery,
)
from app.application.result import Failure


@dataclass
class CategoryHandlers:
    """Groups all category command and query handlers for injection into CategoryApplicationService."""

    create: CreateCategoryHandler
    update: UpdateCategoryHandler
    delete: DeleteCategoryHandler
    get: GetCategoryHandler
    list_all: ListCategoriesHandler
    search: SearchCategoriesHandler


class CategoryApplicationService(ICategoryApplicationService):
    """Implements ICategoryApplicationService by coordinating command/query handlers.

    Each method delegates to the appropriate handler, unwraps the
    ``Result[DTO, DomainError]`` and either returns the DTO or raises
    the domain error — keeping the Result monad internal to the
    application layer.
    """

    def __init__(self, handlers: CategoryHandlers) -> None:
        """Wire the service with its grouped command and query handlers."""
        self._handlers = handlers

    async def create_category(
        self, name: str, description: str, slug: str | None
    ) -> CategoryOutputDTO:
        """Create a new category and return its DTO."""
        result = await self._handlers.create.handle(
            CreateCategoryCommand(name=name, description=description, slug=slug)
        )
        if isinstance(result, Failure):
            raise result.error
        return result.value

    async def get_category(self, category_id: uuid.UUID) -> CategoryOutputDTO:
        """Return the DTO for an existing category.  Raises CategoryNotFoundError if absent."""
        result = await self._handlers.get.handle(GetCategoryQuery(category_id=category_id))
        if isinstance(result, Failure):
            raise result.error
        return result.value

    async def list_categories(
        self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
    ) -> PaginatedResult[CategoryOutputDTO]:
        """Return paginated DTOs with total count and navigation metadata."""
        result = await self._handlers.list_all.handle(
            ListCategoriesQuery(limit=limit, offset=offset)
        )
        if isinstance(result, Failure):
            raise result.error
        return result.value

    async def update_category(
        self,
        category_id: uuid.UUID,
        name: str | None,
        description: str | None,
        slug: str | None,
    ) -> CategoryOutputDTO:
        """Update category fields and return the updated DTO.  Raises CategoryNotFoundError if absent."""
        result = await self._handlers.update.handle(
            UpdateCategoryCommand(
                category_id=category_id, name=name, description=description, slug=slug
            )
        )
        if isinstance(result, Failure):
            raise result.error
        return result.value

    async def delete_category(self, category_id: uuid.UUID) -> None:
        """Delete a category.  Idempotent: succeeds silently if the category does not exist."""
        result = await self._handlers.delete.handle(
            DeleteCategoryCommand(category_id=category_id)
        )
        if isinstance(result, Failure):
            raise result.error

    async def search_categories(
        self, params: CategorySearchParams
    ) -> PaginatedResult[CategoryOutputDTO]:
        """Search categories with filter and pagination metadata."""
        result = await self._handlers.search.handle(
            SearchCategoriesQuery(
                name_contains=params.name_contains,
                slug=params.slug,
                limit=params.limit,
                offset=params.offset,
            )
        )
        if isinstance(result, Failure):
            raise result.error
        return result.value
