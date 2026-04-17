"""Outbound port: IUnitOfWork.

Placed in the *application* layer because the Unit of Work pattern is an
application-level orchestration concern: it wraps repository operations
and event publication into a single atomic boundary that command handlers
consume.  It is *not* a domain concept — the domain only knows about
aggregates and their invariants.

Port placement rationale
------------------------
* Domain layer  → defines ``IItemRepository`` (what the domain needs to
  persist aggregates) and ``IDomainEventPublisher`` (how events leave the
  aggregate).  These are true domain outbound ports.
* Application layer → defines ``IUnitOfWork`` (how a command handler
  groups persistence + event dispatch into one transaction).  Command
  handlers are the only consumers; they live in the application layer too.
* Infrastructure → concrete adapters (SQLAlchemyUnitOfWork,
  InMemoryUnitOfWork) implement this interface.

Generic design
--------------
``IUnitOfWork`` is parameterised by the repository type ``R`` so that the
same port can be reused for any aggregate without coupling the abstract
contract to a specific repository interface.  Command handlers specialise
the type to make mypy aware of the concrete repository they expect::

    class CreateItemHandler:
        def __init__(self, uow: IUnitOfWork[IItemRepository]) -> None: ...

Concrete implementations fix the type parameter::

    class SQLAlchemyUnitOfWork(IUnitOfWork[IItemRepository]): ...
    class SQLAlchemyCategoryUnitOfWork(IUnitOfWork[ICategoryRepository]): ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Generic, TypeVar

from app.domain.events.base import DomainEvent

R = TypeVar("R")


class IUnitOfWork(ABC, Generic[R]):
    """Abstract async context manager that wraps a transactional boundary.

    Type parameter ``R`` is the repository exposed by this unit of work.
    Specialise it at the call site to get full static type-checking::

        async with uow:                          # uow: IUnitOfWork[IItemRepository]
            item = Item.create(...)
            await uow.repository.save(item)      # repository is IItemRepository
            uow.collect(item.collect_events())
            await uow.commit()                   # persist + publish events atomically

    If an exception escapes the ``async with`` block, ``rollback`` is
    called automatically via ``__aexit__``.
    """

    repository: R

    async def __aenter__(self) -> IUnitOfWork[R]:
        """Enter the transactional boundary."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Roll back automatically if an exception escaped the block."""
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    def collect(self, events: list[DomainEvent]) -> None:
        """Enqueue domain events to be published on the next commit."""

    @abstractmethod
    async def commit(self) -> None:
        """Flush pending changes and publish collected domain events."""

    @abstractmethod
    async def rollback(self) -> None:
        """Discard pending changes without publishing events."""
