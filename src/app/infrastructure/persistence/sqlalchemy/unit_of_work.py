"""SQLAlchemy generic implementation of IUnitOfWork.

Wraps an ``async_sessionmaker`` and manages the session lifecycle.

Generic design
--------------
``SQLAlchemyUnitOfWork`` is parameterised by ``TRepo`` via ``repo_factory``
so the same class handles *any* aggregate repository without duplication.
Previously each aggregate required its own UoW subclass (e.g.
``SQLAlchemyCategoryUnitOfWork``); that is no longer needed.

Usage::

    uow = SQLAlchemyUnitOfWork(
        session_factory=session_factory,
        repo_factory=SQLAlchemyItemRepository,
        publisher=publisher,
        use_outbox=True,
    )
    async with uow:
        await uow.repository.save(item)   # uow.repository is SQLAlchemyItemRepository
        uow.collect(item.collect_events())
        await uow.commit()

Two publishing modes are supported via the ``use_outbox`` flag:

* ``use_outbox=False`` (default): flush + commit the session, then dispatch
  domain events in-process via the injected ``IDomainEventPublisher``.

* ``use_outbox=True``: write domain events into the ``outbox`` table *within
  the same session* before committing, so the aggregate change and the event
  row are durable in a single atomic transaction.  The ``OutboxRelay`` worker
  picks up the rows and forwards them to the downstream publisher.
"""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.events.base import DomainEvent
from app.domain.ports.outbound.event_publisher import IDomainEventPublisher
from app.application.ports.unit_of_work import IUnitOfWork
from app.infrastructure.events.outbox_publisher import OutboxEventPublisher

TRepo = TypeVar("TRepo")


class SQLAlchemyUnitOfWork(IUnitOfWork[TRepo], Generic[TRepo]):
    """Generic async SQLAlchemy unit of work.

    The repository type is determined at construction time via ``repo_factory``,
    so one class serves all aggregates.

    Opens a new session on ``__aenter__`` and closes it on ``__aexit__``.

    When ``use_outbox=True``:
      - Events are inserted into the ``outbox`` table as part of the session
        before the commit, guaranteeing atomicity with the aggregate write.
      - The relay dispatches them asynchronously after commit.

    When ``use_outbox=False``:
      - Events are dispatched in-process immediately after the DB commit.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repo_factory: Callable[[AsyncSession], TRepo],
        publisher: IDomainEventPublisher,
        use_outbox: bool = False,
    ) -> None:
        """Initialise the UoW with a session factory, repo factory, publisher and outbox flag."""
        self._session_factory = session_factory
        self._repo_factory = repo_factory
        self._publisher = publisher
        self._use_outbox = use_outbox
        self._pending_events: list[DomainEvent] = []
        self._session: AsyncSession | None = None
        self._active_publisher: IDomainEventPublisher = publisher

    async def __aenter__(self) -> SQLAlchemyUnitOfWork[TRepo]:
        """Open a new async session, build the repository and select the publisher."""
        self._session = self._session_factory()
        self.repository = self._repo_factory(self._session)
        self._active_publisher = (
            OutboxEventPublisher(self._session) if self._use_outbox else self._publisher
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Roll back on exception, then close the session."""
        if exc_type is not None:
            await self.rollback()
        if self._session is not None:
            await self._session.close()

    def collect(self, events: list[DomainEvent]) -> None:
        """Enqueue domain events to be published on commit."""
        self._pending_events.extend(events)

    async def commit(self) -> None:
        """Persist changes and dispatch domain events.

        * Outbox mode: inserts event rows into the session *before* committing
          so both the aggregate and the events land in the same transaction.
        * In-process mode: commits first, then dispatches immediately.
        """
        if self._session is not None:
            if self._use_outbox:
                # Write outbox rows into the session (no flush yet)
                for event in self._pending_events:
                    await self._active_publisher.publish(event)
                self._pending_events.clear()
                # Flush + commit aggregate AND outbox rows atomically
                await self._session.flush()
                await self._session.commit()
            else:
                # Commit aggregate changes first
                await self._session.flush()
                await self._session.commit()
                # Then dispatch in-process (data is durable before handlers see it)
                for event in self._pending_events:
                    await self._active_publisher.publish(event)
                self._pending_events.clear()

    async def rollback(self) -> None:
        """Roll back the session and discard pending events."""
        if self._session is not None:
            await self._session.rollback()
        self._pending_events.clear()
