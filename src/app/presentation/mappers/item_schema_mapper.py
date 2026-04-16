"""Schema <-> DTO mapper for the presentation layer.

Keeps presentation schemas decoupled from application DTOs.
"""

from __future__ import annotations

from app.application.dtos.item_dtos import ItemInputDTO, ItemOutputDTO, ItemUpdateDTO
from app.presentation.api.v1.schemas.item_schemas import CreateItemRequest, ItemResponse, UpdateItemRequest


class ItemSchemaMapper:
    """Maps between presentation API schemas and application DTOs."""

    @staticmethod
    def to_input_dto(request: CreateItemRequest) -> ItemInputDTO:
        """Convert a create request schema to an application input DTO."""
        return ItemInputDTO(
            name=request.name,
            price=request.price,
            description=request.description,
        )

    @staticmethod
    def to_update_dto(request: UpdateItemRequest) -> ItemUpdateDTO:
        """Convert an update request schema to an application update DTO."""
        return ItemUpdateDTO(
            name=request.name,
            price=request.price,
            description=request.description,
        )

    @staticmethod
    def to_response(dto: ItemOutputDTO) -> ItemResponse:
        """Convert an application output DTO to an API response schema."""
        return ItemResponse(
            id=dto.id,
            name=dto.name,
            price=dto.price,
            description=dto.description,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def to_response_list(dtos: list[ItemOutputDTO]) -> list[ItemResponse]:
        """Convert a list of application output DTOs to API response schemas."""
        return [ItemSchemaMapper.to_response(dto) for dto in dtos]
