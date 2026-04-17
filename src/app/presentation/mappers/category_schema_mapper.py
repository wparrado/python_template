"""Schema <-> DTO mapper for the category presentation layer.

Keeps presentation schemas decoupled from application DTOs.
"""

from __future__ import annotations

from typing import Protocol

from app.application.dtos.category_dtos import CategoryOutputDTO, CategorySearchParams
from app.application.dtos.pagination import PaginatedResult
from app.presentation.api.v1.schemas.category_schemas import (
    CategoryResponse,
    PaginatedCategoryResponse,
)


class _HasCategorySearchFilters(Protocol):
    name_contains: str | None
    slug: str | None


class _HasPagination(Protocol):
    limit: int
    offset: int


class CategorySchemaMapper:
    """Maps between presentation API schemas and application DTOs."""

    @staticmethod
    def to_response(dto: CategoryOutputDTO) -> CategoryResponse:
        """Convert an application output DTO to an API response schema."""
        return CategoryResponse(
            id=dto.id,
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def to_response_list(dtos: list[CategoryOutputDTO]) -> list[CategoryResponse]:
        """Convert a list of application output DTOs to API response schemas."""
        return [CategorySchemaMapper.to_response(dto) for dto in dtos]

    @staticmethod
    def to_paginated_response(
        paginated: PaginatedResult[CategoryOutputDTO],
    ) -> PaginatedCategoryResponse:
        """Convert a PaginatedResult of DTOs to a PaginatedCategoryResponse schema."""
        return PaginatedCategoryResponse(
            items=CategorySchemaMapper.to_response_list(paginated.items),
            total=paginated.total,
            limit=paginated.limit,
            offset=paginated.offset,
            has_next=paginated.has_next,
            has_previous=paginated.has_previous,
        )

    @staticmethod
    def to_search_params(filters: _HasCategorySearchFilters, pagination: _HasPagination) -> CategorySearchParams:
        """Build a ``CategorySearchParams`` DTO from FastAPI dependency objects."""
        return CategorySearchParams(
            name_contains=filters.name_contains,
            slug=filters.slug,
            limit=pagination.limit,
            offset=pagination.offset,
        )
