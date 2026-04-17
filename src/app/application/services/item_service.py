"""ItemApplicationService — concrete implementation of the inbound port.

Orchestrates command and query handlers, translates Result values into
either a return value or a raised domain exception, and exposes a clean
async interface to the presentation layer.

The service is the boundary between presentation and application:
  - Presentation calls the IItemApplicationService Protocol.
  - This class fulfils that Protocol.
  - Domain errors propagate as exceptions; the presentation layer maps
    them to HTTP responses via the registered error handlers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.application.commands.item_commands import (
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from app.application.constants import DEFAULT_PAGE_SIZE
from app.application.dtos.item_dtos import ItemOutputDTO, ItemSearchParams
from app.application.dtos.pagination import PaginatedResult
from app.application.handlers.command_handlers import (
    CreateItemHandler,
    DeleteItemHandler,
    UpdateItemHandler,
)
from app.application.handlers.query_handlers import GetItemHandler, ListItemsHandler, SearchItemsHandler
from app.application.ports.item_application_service import IItemApplicationService
from app.application.queries.item_queries import GetItemQuery, ListItemsQuery, SearchItemsQuery
from app.application.result import Failure


@dataclass
class ItemHandlers:
    """Groups all item command and query handlers for injection into ItemApplicationService."""

    create: CreateItemHandler
    update: UpdateItemHandler
    delete: DeleteItemHandler
    get: GetItemHandler
    list_all: ListItemsHandler
    search: SearchItemsHandler


class ItemApplicationService(IItemApplicationService):
    """Implements IItemApplicationService by coordinating command/query handlers.

    Each method delegates to the appropriate handler, unwraps the
    ``Result[DTO, DomainError]`` and either returns the DTO or raises
    the domain error — keeping the Result monad internal to the
    application layer.
    """

    def __init__(self, handlers: ItemHandlers) -> None:
        """Wire the service with its grouped command and query handlers."""
        self._handlers = handlers

    async def create_item(
        self, name: str, price: Decimal, description: str, category_id: uuid.UUID | None = None
    ) -> ItemOutputDTO:
        """Create a new item and return its DTO."""
        result = await self._handlers.create.handle(
            CreateItemCommand(name=name, price=price, description=description, category_id=category_id)
        )
        if isinstance(result, Failure):
            raise result.error
        return result.value

    async def get_item(self, item_id: uuid.UUID) -> ItemOutputDTO:
        """Return the DTO for an existing item.  Raises ItemNotFoundError if absent."""
        result = await self._handlers.get.handle(GetItemQuery(item_id=item_id))
        if isinstance(result, Failure):
            raise result.error
        return result.value

    async def list_items(self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> PaginatedResult[ItemOutputDTO]:
        """Return paginated DTOs with total count and navigation metadata."""
        result = await self._handlers.list_all.handle(ListItemsQuery(limit=limit, offset=offset))
        if isinstance(result, Failure):
            raise result.error
        return result.value

    async def update_item(
        self,
        item_id: uuid.UUID,
        name: str | None,
        price: Decimal | None,
        description: str | None,
        category_id: uuid.UUID | None = None,
    ) -> ItemOutputDTO:
        """Update item fields and return the updated DTO.  Raises ItemNotFoundError if absent."""
        result = await self._handlers.update.handle(
            UpdateItemCommand(item_id=item_id, name=name, price=price, description=description, category_id=category_id)
        )
        if isinstance(result, Failure):
            raise result.error
        return result.value

    async def delete_item(self, item_id: uuid.UUID) -> None:
        """Delete an item.  Idempotent: succeeds silently if the item does not exist."""
        result = await self._handlers.delete.handle(DeleteItemCommand(item_id=item_id))
        if isinstance(result, Failure):
            raise result.error

    async def search_items(self, params: ItemSearchParams) -> PaginatedResult[ItemOutputDTO]:
        """Search items with filter and pagination metadata."""
        result = await self._handlers.search.handle(
            SearchItemsQuery(
                min_price=params.min_price,
                max_price=params.max_price,
                name_contains=params.name_contains,
                limit=params.limit,
                offset=params.offset,
            )
        )
        if isinstance(result, Failure):
            raise result.error
        return result.value
