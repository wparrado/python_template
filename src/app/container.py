"""Dependency Injection container.

Wires all ports to their adapter implementations.
Change an adapter here without touching any domain or application code.
"""

from __future__ import annotations

from app.application.handlers.command_handlers import (
    CreateItemHandler,
    DeleteItemHandler,
    UpdateItemHandler,
)
from app.application.handlers.query_handlers import GetItemHandler, ListItemsHandler
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository
from app.settings import Settings


class Container:
    """Simple manual DI container.

    For a larger application, replace with dependency-injector's
    DeclarativeContainer for auto-wiring, scoping, and overrides.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Infrastructure adapters (singletons)
        self._item_repository = InMemoryItemRepository()
        self._event_publisher = InProcessEventPublisher()

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def create_item_handler(self) -> CreateItemHandler:
        """Return a CreateItemHandler wired to the configured adapters."""
        return CreateItemHandler(
            repository=self._item_repository,
            publisher=self._event_publisher,
        )

    def update_item_handler(self) -> UpdateItemHandler:
        """Return an UpdateItemHandler wired to the configured adapters."""
        return UpdateItemHandler(
            repository=self._item_repository,
            publisher=self._event_publisher,
        )

    def delete_item_handler(self) -> DeleteItemHandler:
        """Return a DeleteItemHandler wired to the configured adapters."""
        return DeleteItemHandler(
            repository=self._item_repository,
            publisher=self._event_publisher,
        )

    # ------------------------------------------------------------------
    # Query handlers
    # ------------------------------------------------------------------

    def get_item_handler(self) -> GetItemHandler:
        """Return a GetItemHandler wired to the configured adapters."""
        return GetItemHandler(repository=self._item_repository)

    def list_items_handler(self) -> ListItemsHandler:
        """Return a ListItemsHandler wired to the configured adapters."""
        return ListItemsHandler(repository=self._item_repository)
