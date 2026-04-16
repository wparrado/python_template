"""Inbound port: IItemApplicationService.

Primary (driving) port — defines the contract that the presentation
layer uses to call item-related use cases.
The application layer implements this via command/query handlers.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.model.example.item import Item


class IItemApplicationService(Protocol):
    """Primary (driving) port for item operations."""

    async def create_item(self, name: str, price: float, description: str) -> Item:
        """Create a new item and return the resulting aggregate."""

    async def get_item(self, item_id: uuid.UUID) -> Item:
        """Return the item with the given ID."""

    async def list_items(self) -> list[Item]:
        """Return all items."""

    async def update_item(
        self,
        item_id: uuid.UUID,
        name: str | None,
        price: float | None,
        description: str | None,
    ) -> Item:
        """Update item fields and return the updated aggregate."""

    async def delete_item(self, item_id: uuid.UUID) -> None:
        """Delete the item with the given ID."""
