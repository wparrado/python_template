"""Item query handlers (CQRS — read side).

Handlers use the same outbound ports as command handlers.
In a production system, query handlers may use optimized read
models (e.g., a read-only DB view) instead of the aggregate store.

Imports only from app.domain and app.application.
"""

from __future__ import annotations

from app.application.dtos.item_dtos import ItemOutputDTO
from app.application.mappers.item_mapper import ItemMapper
from app.application.queries.item_queries import GetItemQuery, ListItemsQuery
from app.application.result import Failure, Result, Success
from app.domain.exceptions.domain_errors import DomainError, ItemNotFoundError
from app.domain.ports.outbound.item_repository import IItemRepository


class GetItemHandler:
    """Handles GetItemQuery — fetches a single item by ID."""

    def __init__(self, repository: IItemRepository) -> None:
        self._repository = repository

    async def handle(self, query: GetItemQuery) -> Result[ItemOutputDTO, DomainError]:
        """Execute the query and return the item or a NotFoundError."""
        item = await self._repository.find_by_id(query.item_id)
        if item is None:
            return Failure(ItemNotFoundError(str(query.item_id)))
        return Success(ItemMapper.to_output_dto(item))


class ListItemsHandler:
    """Handles ListItemsQuery — returns a paginated list of items."""

    def __init__(self, repository: IItemRepository) -> None:
        self._repository = repository

    async def handle(self, query: ListItemsQuery) -> Result[list[ItemOutputDTO], DomainError]:
        """Execute the query and return paginated items."""
        items = await self._repository.find_all(limit=query.limit, offset=query.offset)
        return Success(ItemMapper.to_output_dto_list(items))
