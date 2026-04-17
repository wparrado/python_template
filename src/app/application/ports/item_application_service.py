"""Inbound port: IItemApplicationService.

Primary (driving) port — defines the contract that the presentation
layer uses to interact with item use cases.  Returning application DTOs
means the presentation layer never needs to depend on domain model types.

This port belongs to the application layer, not the domain.  The domain
defines what it *needs* (outbound ports).  The application layer defines
what it *offers* (inbound ports / use-case API).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Protocol

from app.application.constants import DEFAULT_PAGE_SIZE
from app.application.dtos.item_dtos import ItemOutputDTO, ItemSearchParams
from app.application.dtos.pagination import PaginatedResult

__all__ = ["IItemApplicationService"]


class IItemApplicationService(Protocol):
    """Primary (driving) port for item operations.

    Implementations orchestrate domain aggregates and return application
    DTOs.  Errors are surfaced as domain exceptions (re-exported via
    ``app.application.exceptions``) so that the presentation layer can
    handle them without importing from the domain directly.
    """

    async def create_item(self, name: str, price: Decimal, description: str, category_id: uuid.UUID | None = None) -> ItemOutputDTO:
        """Create a new item and return its DTO."""

    async def get_item(self, item_id: uuid.UUID) -> ItemOutputDTO:
        """Return the DTO for an existing item.  Raises ItemNotFoundError if absent."""

    async def list_items(self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> PaginatedResult[ItemOutputDTO]:
        """Return paginated DTOs.  limit caps the result size; offset skips leading items."""

    async def update_item(
        self,
        item_id: uuid.UUID,
        name: str | None,
        price: Decimal | None,
        description: str | None,
        category_id: uuid.UUID | None = None,
    ) -> ItemOutputDTO:
        """Update item fields and return the updated DTO.  Raises ItemNotFoundError if absent."""

    async def delete_item(self, item_id: uuid.UUID) -> None:
        """Delete an item.  Idempotent: succeeds silently if the item does not exist."""

    async def search_items(self, params: ItemSearchParams) -> PaginatedResult[ItemOutputDTO]:
        """Search items using optional price range and name filters.

        *params* groups all filter and pagination fields.  Omit any field to
        leave that dimension unconstrained.
        """
