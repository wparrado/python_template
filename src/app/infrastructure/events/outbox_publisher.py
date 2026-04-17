"""OutboxEventPublisher — writes domain events into the outbox table.

This adapter implements IDomainEventPublisher by persisting events to the
``outbox`` table within the *current* SQLAlchemy session — the same session
that is committing the aggregate change.  Because both writes share a single
transaction, the guarantee is absolute:

  - If the transaction commits → event row is durable → relay will dispatch it.
  - If the transaction rolls back → event row is discarded atomically.

No network call, no broker dependency, no dual-write problem.

The OutboxRelay is responsible for reading the persisted rows and forwarding
them to the actual downstream publisher (in-process handlers, message broker, etc).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events.base import DomainEvent
from app.domain.ports.outbound.event_publisher import IDomainEventPublisher
from app.infrastructure.events.serialization import serialize
from app.infrastructure.persistence.sqlalchemy.models import OutboxORM


class OutboxEventPublisher(IDomainEventPublisher):
    """Persists domain events into the outbox table within the active session.

    This publisher must be used inside an open ``AsyncSession`` that will be
    committed by the enclosing ``SQLAlchemyUnitOfWork``.  It does *not* flush
    or commit; the UoW is responsible for that.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Bind the publisher to an open SQLAlchemy async session."""
        self._session = session

    async def publish(self, event: DomainEvent) -> None:
        """Insert an outbox row for *event* into the current session."""
        row = OutboxORM(
            id=uuid.uuid4(),
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            payload=serialize(event),
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
