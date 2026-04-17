"""Category query handlers (CQRS — read side).

Handlers use the same outbound ports as command handlers.
In a production system, query handlers may use optimized read
models (e.g., a read-only DB view) instead of the aggregate store.

Imports only from app.domain and app.application.
"""

from __future__ import annotations

from app.application.dtos.category_dtos import CategoryOutputDTO
from app.application.dtos.pagination import PaginatedResult
from app.application.mappers.category_mapper import CategoryMapper
from app.application.queries.category_queries import (
    GetCategoryQuery,
    ListCategoriesQuery,
    SearchCategoriesQuery,
)
from app.application.result import Failure, Result, Success
from app.domain.exceptions.domain_errors import CategoryNotFoundError, DomainError
from app.domain.model.example.category import Category
from app.domain.ports.outbound.category_repository import ICategoryRepository
from app.domain.specifications.base import Specification
from app.domain.specifications.category_specifications import (
    ActiveCategorySpecification,
    AllCategoriesSpecification,
    NameContainsCategorySpecification,
    SlugMatchesSpecification,
)


class GetCategoryHandler:
    """Handles GetCategoryQuery — fetches a single category by ID."""

    def __init__(self, repository: ICategoryRepository) -> None:
        self._repository = repository

    async def handle(self, query: GetCategoryQuery) -> Result[CategoryOutputDTO, DomainError]:
        """Execute the query and return the category or a NotFoundError."""
        category = await self._repository.find_by_id(query.category_id)
        if category is None:
            return Failure(CategoryNotFoundError(str(query.category_id)))
        return Success(CategoryMapper.to_output_dto(category))


class ListCategoriesHandler:
    """Handles ListCategoriesQuery — returns a paginated list of categories with total count."""

    def __init__(self, repository: ICategoryRepository) -> None:
        self._repository = repository

    async def handle(
        self, query: ListCategoriesQuery
    ) -> Result[PaginatedResult[CategoryOutputDTO], DomainError]:
        """Execute the query and return paginated categories with metadata."""
        categories = await self._repository.find_all(limit=query.limit, offset=query.offset)
        total = await self._repository.count()
        return Success(
            PaginatedResult(
                items=CategoryMapper.to_output_dto_list(categories),
                total=total,
                limit=query.limit,
                offset=query.offset,
            )
        )


class SearchCategoriesHandler:
    """Handles SearchCategoriesQuery — filters categories using composable specifications."""

    def __init__(self, repository: ICategoryRepository) -> None:
        self._repository = repository

    async def handle(
        self, query: SearchCategoriesQuery
    ) -> Result[PaginatedResult[CategoryOutputDTO], DomainError]:
        """Build a composite specification from query params and delegate to the repository."""
        spec = self._build_spec(query)
        all_matching = await self._repository.find_matching(spec)
        total = len(all_matching)
        paginated = all_matching[query.offset : query.offset + query.limit]
        return Success(
            PaginatedResult(
                items=CategoryMapper.to_output_dto_list(paginated),
                total=total,
                limit=query.limit,
                offset=query.offset,
            )
        )

    @staticmethod
    def _build_spec(query: SearchCategoriesQuery) -> Specification[Category]:
        """Compose a specification from the optional filter parameters."""
        base: Specification[Category] = (
            AllCategoriesSpecification() if query.include_deleted else ActiveCategorySpecification()
        )
        if query.name_contains is not None:
            base = base & NameContainsCategorySpecification(query.name_contains)
        if query.slug is not None:
            base = base & SlugMatchesSpecification(query.slug)
        return base
