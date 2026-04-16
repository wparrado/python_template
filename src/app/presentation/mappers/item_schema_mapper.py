"""Schema <-> DTO mapper for the presentation layer.

Keeps presentation schemas decoupled from application DTOs.
The Decimal-to-float conversion for responses happens here —
at the presentation boundary — intentionally.
"""

from __future__ import annotations

from app.application.dtos.item_dtos import ItemOutputDTO
from app.presentation.api.v1.schemas.item_schemas import ItemResponse


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
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def to_response_list(dtos: list[ItemOutputDTO]) -> list[ItemResponse]:
        """Convert a list of application output DTOs to API response schemas."""
        return [ItemSchemaMapper.to_response(dto) for dto in dtos]
