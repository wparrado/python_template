"""Inbound port: ICategoryApplicationService.

Primary (driving) port — defines the contract that the presentation
layer uses to interact with category use cases.  Returning application DTOs
means the presentation layer never needs to depend on domain model types.

This port belongs to the application layer, not the domain.  The domain
defines what it *needs* (outbound ports).  The application layer defines
what it *offers* (inbound ports / use-case API).
"""

from __future__ import annotations

import uuid
from typing import Protocol

from app.application.constants import DEFAULT_PAGE_SIZE
from app.application.dtos.category_dtos import CategoryOutputDTO, CategorySearchParams
from app.application.dtos.pagination import PaginatedResult

__all__ = ["ICategoryApplicationService"]


class ICategoryApplicationService(Protocol):
    """Primary (driving) port for category operations.

    Implementations orchestrate domain aggregates and return application
    DTOs.  Errors are surfaced as domain exceptions so that the presentation
    layer can handle them without importing from the domain directly.
    """

    async def create_category(
        self, name: str, description: str, slug: str | None
    ) -> CategoryOutputDTO:
        """Create a new category and return its DTO."""

    async def get_category(self, category_id: uuid.UUID) -> CategoryOutputDTO:
        """Return the DTO for an existing category.  Raises CategoryNotFoundError if absent."""

    async def list_categories(
        self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
    ) -> PaginatedResult[CategoryOutputDTO]:
        """Return paginated DTOs.  limit caps the result size; offset skips leading categories."""

    async def update_category(
        self,
        category_id: uuid.UUID,
        name: str | None,
        description: str | None,
        slug: str | None,
    ) -> CategoryOutputDTO:
        """Update category fields and return the updated DTO.  Raises CategoryNotFoundError if absent."""

    async def delete_category(self, category_id: uuid.UUID) -> None:
        """Delete a category.  Idempotent: succeeds silently if the category does not exist."""

    async def search_categories(
        self, params: CategorySearchParams
    ) -> PaginatedResult[CategoryOutputDTO]:
        """Search categories using optional name and slug filters.

        *params* groups all filter and pagination fields.  Omit any field to
        leave that dimension unconstrained.
        """
