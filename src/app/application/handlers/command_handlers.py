"""Item command handlers (CQRS — write side).

Handlers orchestrate domain operations:
  1. Load aggregate from repository
  2. Execute domain method (enforces invariants, emits events)
  3. Persist changes
  4. Publish domain events
  5. Return Result[DTO, DomainError]

Imports only from app.domain and app.application.
"""

from __future__ import annotations

from app.application.commands.item_commands import (
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from app.application.dtos.item_dtos import ItemOutputDTO
from app.application.mappers.item_mapper import ItemMapper
from app.application.result import Failure, Result, Success
from app.domain.exceptions.domain_errors import DomainError, ItemNotFoundError
from app.domain.model.example.item import Item
from app.domain.ports.outbound.event_publisher import IDomainEventPublisher
from app.domain.ports.outbound.item_repository import IItemRepository


class CreateItemHandler:
    """Handles CreateItemCommand — creates and persists a new Item."""

    def __init__(self, repository: IItemRepository, publisher: IDomainEventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    async def handle(self, command: CreateItemCommand) -> Result[ItemOutputDTO, DomainError]:
        """Execute the command and return the created item DTO or a DomainError."""
        try:
            item = Item.create(
                name=command.name,
                price=command.price,
                description=command.description,
            )
            await self._repository.save(item)
            await self._publisher.publish_all(item.collect_events())
            return Success(ItemMapper.to_output_dto(item))
        except DomainError as exc:
            return Failure(exc)


class UpdateItemHandler:
    """Handles UpdateItemCommand — updates fields on an existing Item."""

    def __init__(self, repository: IItemRepository, publisher: IDomainEventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    async def handle(self, command: UpdateItemCommand) -> Result[ItemOutputDTO, DomainError]:
        """Execute the command and return the updated item DTO or a DomainError."""
        try:
            item = await self._repository.find_by_id(command.item_id)
            if item is None:
                return Failure(ItemNotFoundError(str(command.item_id)))
            item.update(name=command.name, price=command.price, description=command.description)
            await self._repository.save(item)
            await self._publisher.publish_all(item.collect_events())
            return Success(ItemMapper.to_output_dto(item))
        except DomainError as exc:
            return Failure(exc)


class DeleteItemHandler:
    """Handles DeleteItemCommand — removes an Item by ID."""

    def __init__(self, repository: IItemRepository, publisher: IDomainEventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    async def handle(self, command: DeleteItemCommand) -> Result[None, DomainError]:
        """Execute the command and return Success(None) or a DomainError."""
        try:
            item = await self._repository.find_by_id(command.item_id)
            if item is None:
                return Failure(ItemNotFoundError(str(command.item_id)))
            item.mark_deleted()
            await self._repository.delete(command.item_id)
            await self._publisher.publish_all(item.collect_events())
            return Success(None)
        except DomainError as exc:
            return Failure(exc)
