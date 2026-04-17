"""Item query handlers (CQRS — read side).

Handlers use the same outbound ports as command handlers.
In a production system, query handlers may use optimized read
models (e.g., a read-only DB view) instead of the aggregate store.

Imports only from app.domain and app.application.
"""

from __future__ import annotations

from app.application.dtos.item_dtos import ItemOutputDTO
from app.application.dtos.pagination import PaginatedResult
from app.application.mappers.item_mapper import ItemMapper
from app.application.queries.item_queries import GetItemQuery, ListItemsQuery, SearchItemsQuery
from app.application.result import Failure, Result, Success
from app.domain.exceptions.domain_errors import DomainError, ItemNotFoundError
from app.domain.model.example.item import Item
from app.domain.ports.outbound.item_repository import IItemRepository
from app.domain.specifications.base import Specification
from app.domain.specifications.item_specifications import (
    ActiveItemSpecification,
    AllItemsSpecification,
    NameContainsSpecification,
    PriceInRangeSpecification,
)


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
    """Handles ListItemsQuery — returns a paginated list of items with total count."""

    def __init__(self, repository: IItemRepository) -> None:
        self._repository = repository

    async def handle(self, query: ListItemsQuery) -> Result[PaginatedResult[ItemOutputDTO], DomainError]:
        """Execute the query and return paginated items with metadata."""
        items = await self._repository.find_all(limit=query.limit, offset=query.offset)
        total = await self._repository.count()
        return Success(
            PaginatedResult(
                items=ItemMapper.to_output_dto_list(items),
                total=total,
                limit=query.limit,
                offset=query.offset,
            )
        )


class SearchItemsHandler:
    """Handles SearchItemsQuery — filters items using composable specifications."""

    def __init__(self, repository: IItemRepository) -> None:
        self._repository = repository

    async def handle(self, query: SearchItemsQuery) -> Result[PaginatedResult[ItemOutputDTO], DomainError]:
        """Build a composite specification from query params and delegate to the repository."""
        spec = self._build_spec(query)
        all_matching = await self._repository.find_matching(spec)
        total = len(all_matching)
        paginated = all_matching[query.offset : query.offset + query.limit]
        return Success(
            PaginatedResult(
                items=ItemMapper.to_output_dto_list(paginated),
                total=total,
                limit=query.limit,
                offset=query.offset,
            )
        )

    @staticmethod
    def _build_spec(query: SearchItemsQuery) -> Specification[Item]:
        """Compose a specification from the optional filter parameters."""
        base: Specification[Item] = AllItemsSpecification() if query.include_deleted else ActiveItemSpecification()
        if query.min_price is not None or query.max_price is not None:
            base = base & PriceInRangeSpecification(query.min_price, query.max_price)
        if query.name_contains is not None:
            base = base & NameContainsSpecification(query.name_contains)
        return base
