"""Schema <-> DTO mapper for the presentation layer.

Keeps presentation schemas decoupled from application DTOs.
The Decimal-to-float conversion for responses happens here —
at the presentation boundary — intentionally.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from app.application.dtos.item_dtos import ItemOutputDTO, ItemSearchParams
from app.application.dtos.pagination import PaginatedResult
from app.presentation.api.v1.schemas.item_schemas import ItemResponse, PaginatedItemResponse


class _HasSearchFilters(Protocol):
    min_price: Decimal | None
    max_price: Decimal | None
    name_contains: str | None


class _HasPagination(Protocol):
    limit: int
    offset: int


class ItemSchemaMapper:
    """Maps between presentation API schemas and application DTOs."""

    @staticmethod
    def to_response(dto: ItemOutputDTO) -> ItemResponse:
        """Convert an application output DTO to an API response schema.

        ``price`` is converted from ``Decimal`` to ``float`` at the HTTP
        boundary.  Monetary precision is preserved inside the application;
        JSON clients receive a standard float representation.
        """
        return ItemResponse(
            id=dto.id,
            name=dto.name,
            price=float(dto.price),
            description=dto.description,
            category_id=dto.category_id,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def to_response_list(dtos: list[ItemOutputDTO]) -> list[ItemResponse]:
        """Convert a list of application output DTOs to API response schemas."""
        return [ItemSchemaMapper.to_response(dto) for dto in dtos]

    @staticmethod
    def to_paginated_response(paginated: PaginatedResult[ItemOutputDTO]) -> PaginatedItemResponse:
        """Convert a PaginatedResult of DTOs to a PaginatedItemResponse schema."""
        return PaginatedItemResponse(
            items=ItemSchemaMapper.to_response_list(paginated.items),
            total=paginated.total,
            limit=paginated.limit,
            offset=paginated.offset,
            has_next=paginated.has_next,
            has_previous=paginated.has_previous,
        )

    @staticmethod
    def to_search_params(filters: _HasSearchFilters, pagination: _HasPagination) -> ItemSearchParams:
        """Build an ``ItemSearchParams`` DTO from FastAPI dependency objects."""
        return ItemSearchParams(
            min_price=filters.min_price,
            max_price=filters.max_price,
            name_contains=filters.name_contains,
            limit=pagination.limit,
            offset=pagination.offset,
        )
