"""Category command handlers (CQRS — write side).

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

from app.application.commands.category_commands import (
    CreateCategoryCommand,
    DeleteCategoryCommand,
    UpdateCategoryCommand,
)
from app.application.dtos.category_dtos import CategoryOutputDTO
from app.application.mappers.category_mapper import CategoryMapper
from app.application.ports.unit_of_work import IUnitOfWork
from app.application.result import Failure, Result, Success
from app.domain.exceptions.domain_errors import CategoryNotFoundError, DomainError
from app.domain.model.example.category import Category
from app.domain.ports.outbound.category_repository import ICategoryRepository
from app.domain.ports.inbound.clock import IClock


class CreateCategoryHandler:
    """Handles CreateCategoryCommand — creates and persists a new Category."""

    def __init__(self, uow: IUnitOfWork[ICategoryRepository]) -> None:
        self._uow = uow

    async def handle(self, command: CreateCategoryCommand) -> Result[CategoryOutputDTO, DomainError]:
        """Execute the command and return the created category DTO or a DomainError."""
        try:
            async with self._uow:
                category = Category.create(
                    name=command.name,
                    description=command.description,
                    slug=command.slug,
                )
                await self._uow.repository.save(category)
                self._uow.collect(category.collect_events())
                await self._uow.commit()
            return Success(CategoryMapper.to_output_dto(category))
        except DomainError as exc:
            return Failure(exc)


class UpdateCategoryHandler:
    """Handles UpdateCategoryCommand — updates fields on an existing Category."""

    def __init__(self, uow: IUnitOfWork[ICategoryRepository], clock: IClock) -> None:
        self._uow = uow
        self._clock = clock

    async def handle(self, command: UpdateCategoryCommand) -> Result[CategoryOutputDTO, DomainError]:
        """Execute the command and return the updated category DTO or a DomainError."""
        try:
            async with self._uow:
                category = await self._uow.repository.find_by_id(command.category_id)
                if category is None:
                    return Failure(CategoryNotFoundError(str(command.category_id)))
                category.update(
                    name=command.name,
                    description=command.description,
                    slug=command.slug,
                    clock=self._clock,
                )
                await self._uow.repository.save(category)
                self._uow.collect(category.collect_events())
                await self._uow.commit()
            return Success(CategoryMapper.to_output_dto(category))
        except DomainError as exc:
            return Failure(exc)


class DeleteCategoryHandler:
    """Handles DeleteCategoryCommand — removes a Category by ID."""

    def __init__(self, uow: IUnitOfWork[ICategoryRepository]) -> None:
        self._uow = uow

    async def handle(self, command: DeleteCategoryCommand) -> Result[None, DomainError]:
        """Execute the command and return Success(None).

        Idempotent: if the category does not exist the operation succeeds silently,
        consistent with HTTP DELETE semantics.
        """
        try:
            async with self._uow:
                category = await self._uow.repository.find_by_id(command.category_id)
                if category is None:
                    return Success(None)
                category.mark_deleted()
                await self._uow.repository.delete(command.category_id)
                self._uow.collect(category.collect_events())
                await self._uow.commit()
            return Success(None)
        except DomainError as exc:
            return Failure(exc)
