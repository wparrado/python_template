"""Item command handlers (CQRS — write side).

Handlers orchestrate domain operations:
  1. Open a Unit of Work (transactional boundary)
  2. Load aggregate from repository
  3. Execute domain method (enforces invariants, emits events)
  4. Persist changes
  5. Commit: persist + publish domain events atomically
  6. Return Result[DTO, DomainError]

Imports only from app.domain and app.application.
"""

from __future__ import annotations

from app.application.commands.item_commands import (
    CATEGORY_ID_UNSET,
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from app.application.dtos.item_dtos import ItemOutputDTO
from app.application.mappers.item_mapper import ItemMapper
from app.application.result import Failure, Result, Success
from app.domain.exceptions.domain_errors import CategoryNotFoundError, DomainError, ItemNotFoundError
from app.domain.model.example.item import Item, _UNSET as _DOMAIN_UNSET
from app.application.ports.unit_of_work import IUnitOfWork
from app.domain.ports.outbound.item_repository import IItemRepository
from app.domain.ports.outbound.category_repository import ICategoryRepository
from app.domain.ports.inbound.clock import IClock


class CreateItemHandler:
    """Handles CreateItemCommand — creates and persists a new Item."""

    def __init__(
        self,
        uow: IUnitOfWork[IItemRepository],
        clock: IClock,
        category_uow: IUnitOfWork[ICategoryRepository] | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._category_uow = category_uow

    async def handle(self, command: CreateItemCommand) -> Result[ItemOutputDTO, DomainError]:
        """Execute the command and return the created item DTO or a DomainError."""
        try:
            if command.category_id is not None and self._category_uow is not None:
                async with self._category_uow:
                    category = await self._category_uow.repository.find_by_id(command.category_id)
                    if category is None:
                        return Failure(CategoryNotFoundError(str(command.category_id)))
            async with self._uow:
                item = Item.create(
                    name=command.name,
                    price=command.price,
                    description=command.description,
                    category_id=command.category_id,
                    clock=self._clock,
                )
                await self._uow.repository.save(item)
                self._uow.collect(item.collect_events())
                await self._uow.commit()
            return Success(ItemMapper.to_output_dto(item))
        except DomainError as exc:
            return Failure(exc)


class UpdateItemHandler:
    """Handles UpdateItemCommand — updates fields on an existing Item."""

    def __init__(
        self,
        uow: IUnitOfWork[IItemRepository],
        clock: IClock,
        category_uow: IUnitOfWork[ICategoryRepository] | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._category_uow = category_uow

    async def handle(self, command: UpdateItemCommand) -> Result[ItemOutputDTO, DomainError]:
        """Execute the command and return the updated item DTO or a DomainError."""
        try:
            if (
                command.category_id is not CATEGORY_ID_UNSET
                and command.category_id is not None
                and self._category_uow is not None
            ):
                async with self._category_uow:
                    cat_repo = self._category_uow.repository
                    category = await cat_repo.find_by_id(command.category_id)  # type: ignore[arg-type]
                    if category is None:
                        return Failure(CategoryNotFoundError(str(command.category_id)))
            async with self._uow:
                item = await self._uow.repository.find_by_id(command.item_id)
                if item is None:
                    return Failure(ItemNotFoundError(str(command.item_id)))
                # Map command sentinel → domain sentinel so the aggregate
                # knows whether to update the category_id or leave it untouched.
                cat_id = (
                    _DOMAIN_UNSET
                    if command.category_id is CATEGORY_ID_UNSET
                    else command.category_id
                )
                item.update(
                    name=command.name,
                    price=command.price,
                    description=command.description,
                    category_id=cat_id,
                    clock=self._clock,
                )
                await self._uow.repository.save(item)
                self._uow.collect(item.collect_events())
                await self._uow.commit()
            return Success(ItemMapper.to_output_dto(item))
        except DomainError as exc:
            return Failure(exc)


class DeleteItemHandler:
    """Handles DeleteItemCommand — removes an Item by ID."""

    def __init__(self, uow: IUnitOfWork[IItemRepository]) -> None:
        self._uow = uow

    async def handle(self, command: DeleteItemCommand) -> Result[None, DomainError]:
        """Execute the command and return Success(None).

        Idempotent: if the item does not exist the operation succeeds silently,
        consistent with HTTP DELETE semantics (a second call yields the same state).
        """
        try:
            async with self._uow:
                item = await self._uow.repository.find_by_id(command.item_id)
                if item is None:
                    return Success(None)
                item.mark_deleted()
                await self._uow.repository.delete(command.item_id)
                self._uow.collect(item.collect_events())
                await self._uow.commit()
            return Success(None)
        except DomainError as exc:
            return Failure(exc)
