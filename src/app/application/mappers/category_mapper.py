"""Category mapper — converts between domain entities and application DTOs.

Mappers are explicit. There is no "magic" serialization.
"""

from __future__ import annotations

from app.application.dtos.category_dtos import CategoryOutputDTO
from app.domain.model.example.category import Category


class CategoryMapper:
    """Converts Category domain entity to/from application DTOs."""

    @staticmethod
    def to_output_dto(category: Category) -> CategoryOutputDTO:
        """Convert a Category aggregate to a CategoryOutputDTO."""
        return CategoryOutputDTO(
            id=category.id,
            name=category.name.value,
            slug=category.slug.value,
            description=category.description.value,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    @staticmethod
    def to_output_dto_list(categories: list[Category]) -> list[CategoryOutputDTO]:
        """Convert a list of Category aggregates to a list of CategoryOutputDTOs."""
        return [CategoryMapper.to_output_dto(cat) for cat in categories]
