"""Item mapper — converts between domain entities and application DTOs.

Mappers are explicit. There is no "magic" serialization.
"""

from __future__ import annotations

from app.application.dtos.item_dtos import ItemOutputDTO
from app.domain.model.example.item import Item


class ItemMapper:
    """Converts Item domain entity to/from application DTOs."""

    @staticmethod
    def to_output_dto(item: Item) -> ItemOutputDTO:
        """Convert an Item aggregate to an ItemOutputDTO."""
        return ItemOutputDTO(
            id=item.id,
            name=item.name,
            price=item.price,
            description=item.description,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def to_output_dto_list(items: list[Item]) -> list[ItemOutputDTO]:
        """Convert a list of Item aggregates to a list of ItemOutputDTOs."""
        return [ItemMapper.to_output_dto(item) for item in items]
