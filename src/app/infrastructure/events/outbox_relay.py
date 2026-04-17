"""OutboxRelay — background worker that dispatches persisted domain events.

Polls the ``outbox`` table for rows where ``published_at IS NULL``, deserializes
each event, forwards it to the configured downstream publisher, then marks the
row as published.  Runs as a long-lived ``asyncio.Task`` started during the
FastAPI lifespan.

Delivery guarantee: **at-least-once**.  If the relay crashes after dispatching
but before updating ``published_at``, the event will be re-dispatched on the next
poll cycle.  Idempotent downstream consumers are recommended.

Multi-worker safety: uses ``SELECT … FOR UPDATE SKIP LOCKED`` so that concurrent
relay workers (e.g. multiple Gunicorn/Granian workers) never process the same row
twice.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ports.outbound.event_publisher import IDomainEventPublisher
from app.infrastructure.events.serialization import deserialize
from app.infrastructure.persistence.sqlalchemy.models import OutboxORM

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_BATCH_SIZE = 50


class OutboxRelay:
    """Polls the outbox table and forwards unpublished events downstream.

    Parameters
    ----------
    session_factory:
        An ``async_sessionmaker`` that produces new ``AsyncSession`` instances.
        Each poll cycle opens and closes its own independent session.
    publisher:
        The downstream ``IDomainEventPublisher`` (typically ``InProcessEventPublisher``
        for local handlers, or a broker adapter for Kafka/RabbitMQ).
    poll_interval:
        Seconds to sleep between poll cycles.  Defaults to 1 second.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: IDomainEventPublisher,
        poll_interval: float = 1.0,
    ) -> None:
        """Initialise the relay without starting the background task."""
        self._session_factory = session_factory
        self._publisher = publisher
        self._poll_interval = poll_interval
        self._task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the relay as a background asyncio task."""
        self._task = asyncio.create_task(self._run(), name="outbox-relay")
        logger.info("outbox_relay.started", poll_interval=self._poll_interval)

    async def stop(self) -> None:
        """Cancel the background task and wait for it to finish."""
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
            logger.info("outbox_relay.stopped")

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        """Main relay loop: poll → dispatch → sleep, forever."""
        while True:
            try:
                await self._process_batch()
            except Exception:
                logger.exception("outbox_relay.poll_error")
            await asyncio.sleep(self._poll_interval)

    async def _process_batch(self) -> None:
        """Fetch up to ``_BATCH_SIZE`` unpublished rows and dispatch them."""
        async with self._session_factory() as session:
            async with session.begin():
                rows = (
                    await session.scalars(
                        select(OutboxORM)
                        .where(OutboxORM.published_at.is_(None))
                        .order_by(OutboxORM.created_at)
                        .limit(_BATCH_SIZE)
                        .with_for_update(skip_locked=True)
                    )
                ).all()

                for row in rows:
                    try:
                        event = deserialize(row.event_type, row.payload)
                        await self._publisher.publish(event)
                        row.published_at = datetime.now(UTC)
                        logger.debug(
                            "outbox_relay.dispatched",
                            event_type=row.event_type,
                            event_id=str(row.id),
                        )
                    except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                        logger.exception(
                            "outbox_relay.dispatch_error",
                            event_type=row.event_type,
                            event_id=str(row.id),
                        )
