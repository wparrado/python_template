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
from app.application.handlers.query_handlers import GetItemHandler, ListItemsHandler, SearchItemsHandler
from app.application.services.item_service import ItemApplicationService, ItemHandlers
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository
from app.settings import Settings


class Container:
    """Simple manual DI container.

    Wires infrastructure adapters to domain ports and application services.
    To swap an adapter (e.g., replace InMemory with SQLAlchemy), create a
    new class that implements the relevant port and update the binding here
    — domain and application code remain untouched.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialise the container and build all singleton adapters."""
        self._settings = settings
        # Infrastructure adapters — one instance shared across all handlers
        self._item_repository = InMemoryItemRepository()
        self._event_publisher = InProcessEventPublisher()

    # ------------------------------------------------------------------
    # Application service (primary port implementation)
    # ------------------------------------------------------------------

    def item_application_service(self) -> ItemApplicationService:
        """Return an ItemApplicationService wired to all required handlers."""
        return ItemApplicationService(
            handlers=ItemHandlers(
                create=self._create_item_handler(),
                update=self._update_item_handler(),
                delete=self._delete_item_handler(),
                get=self._get_item_handler(),
                list_all=self._list_items_handler(),
                search=self._search_items_handler(),
            )
        )

    # ------------------------------------------------------------------
    # Command handlers (private — consumed by the service above)
    # ------------------------------------------------------------------

    def _create_item_handler(self) -> CreateItemHandler:
        """Return a CreateItemHandler wired to the configured adapters."""
        return CreateItemHandler(
            repository=self._item_repository,
            publisher=self._event_publisher,
        )

    def _update_item_handler(self) -> UpdateItemHandler:
        """Return an UpdateItemHandler wired to the configured adapters."""
        return UpdateItemHandler(
            repository=self._item_repository,
            publisher=self._event_publisher,
        )

    def _delete_item_handler(self) -> DeleteItemHandler:
        """Return a DeleteItemHandler wired to the configured adapters."""
        return DeleteItemHandler(
            repository=self._item_repository,
            publisher=self._event_publisher,
        )

    # ------------------------------------------------------------------
    # Query handlers (private — consumed by the service above)
    # ------------------------------------------------------------------

    def _get_item_handler(self) -> GetItemHandler:
        """Return a GetItemHandler wired to the configured adapters."""
        return GetItemHandler(repository=self._item_repository)

    def _list_items_handler(self) -> ListItemsHandler:
        """Return a ListItemsHandler wired to the configured adapters."""
        return ListItemsHandler(repository=self._item_repository)

    def _search_items_handler(self) -> SearchItemsHandler:
        """Return a SearchItemsHandler wired to the configured adapters."""
        return SearchItemsHandler(repository=self._item_repository)
