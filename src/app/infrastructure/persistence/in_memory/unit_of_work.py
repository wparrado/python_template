"""InMemory implementation of IUnitOfWork.

Wraps InMemoryItemRepository and InProcessEventPublisher.
commit() collects events from saved items and dispatches them;
rollback() is a no-op for in-memory storage (nothing to undo).
"""

from __future__ import annotations

from app.domain.events.base import DomainEvent
from app.domain.ports.outbound.event_publisher import IDomainEventPublisher
from app.application.ports.unit_of_work import IUnitOfWork
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository


class InMemoryUnitOfWork(IUnitOfWork[InMemoryItemRepository]):
    """In-process, non-transactional UoW suitable for testing and prototyping.

    Commit publishes all pending domain events collected since the last commit.
    Rollback is a no-op because in-memory operations cannot be undone.
    """

    def __init__(
        self,
        repository: InMemoryItemRepository,
        publisher: IDomainEventPublisher,
    ) -> None:
        self.repository = repository
        self._publisher = publisher
        self._pending_events: list[DomainEvent] = []

    def collect(self, events: list[DomainEvent]) -> None:
        """Enqueue domain events to be published on commit."""
        self._pending_events.extend(events)

    async def commit(self) -> None:
        """Publish all enqueued events and clear the queue."""
        for event in self._pending_events:
            await self._publisher.publish(event)
        self._pending_events.clear()

    async def rollback(self) -> None:
        """Discard pending events (in-memory writes cannot be reversed)."""
        self._pending_events.clear()
