"""RabbitMQEventConsumer — consumes domain events from a RabbitMQ queue.

This adapter subscribes to a durable queue bound to the ``domain.events``
topic exchange and dispatches received events to the in-process publisher.

Typical use-case
----------------
A *second service* (e.g. Notifications) runs this consumer to react to
events produced by the Items service without tight coupling::

    consumer = RabbitMQEventConsumer(
        url="amqp://guest:guest@rabbitmq/",
        exchange="domain.events",
        queue="notifications.items",
        routing_keys=["ItemCreated", "ItemUpdated"],  # '' or '#' for all
        publisher=in_process_publisher,
    )
    await consumer.start()

Requirements
------------
    uv add aio-pika

Delivery semantics
------------------
- Messages are acknowledged **after** successful dispatch so the broker
  re-delivers on crash (at-least-once).
- Duplicate handling is the consumer's responsibility; pair with idempotent
  handlers or a deduplication store.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

try:
    import aio_pika
except ImportError:
    aio_pika = None

from app.infrastructure.events.consumer.base import BrokerEventConsumer
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.events.serialization import deserialize

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class RabbitMQEventConsumer(BrokerEventConsumer):
    """Consumes domain events from a RabbitMQ topic exchange queue.

    Parameters
    ----------
    url:
        AMQP connection URL.
    exchange:
        Topic exchange name to bind the queue to.
    queue:
        Durable queue name.  Use a service-specific name so each service gets
        its own copy of every matching event.
    routing_keys:
        List of routing key patterns, e.g. ``["ItemCreated", "Item.*", "#"]``.
        Defaults to ``["#"]`` (all events).
    publisher:
        The in-process publisher to dispatch deserialized events to.
    """

    def __init__(
        self,
        url: str,
        exchange: str,
        queue: str,
        publisher: InProcessEventPublisher,
        routing_keys: list[str] | None = None,
    ) -> None:
        """Store configuration — does NOT connect yet."""
        self._url = url
        self._exchange = exchange
        self._queue = queue
        self._publisher = publisher
        self._routing_keys = routing_keys or ["#"]
        self._connection: Any | None = None
        self._task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # BrokerEventConsumer
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect to RabbitMQ and start consuming in a background task."""
        if aio_pika is None:
            raise ImportError("aio-pika is required. Install with: uv add aio-pika")

        self._connection = await aio_pika.connect_robust(self._url)
        channel = await self._connection.channel()
        exchange = await channel.declare_exchange(self._exchange, aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(self._queue, durable=True)
        for key in self._routing_keys:
            await queue.bind(exchange, routing_key=key)

        self._task = asyncio.create_task(self._consume(queue), name=f"consumer.{self._queue}")
        logger.info(
            "rabbitmq_consumer.started",
            queue=self._queue,
            exchange=self._exchange,
            routing_keys=self._routing_keys,
        )

    async def stop(self) -> None:
        """Cancel the consumer task and close the connection."""
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
        logger.info("rabbitmq_consumer.stopped", queue=self._queue)

    @property
    def is_running(self) -> bool:
        """Return True when the consumer task is active."""
        return self._task is not None and not self._task.done()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _consume(self, queue: Any) -> None:
        """Main consume loop — ack after successful dispatch."""
        async with queue.iterator() as messages:
            async for message in messages:
                async with message.process():
                    try:
                        event_type = message.headers.get("event_type", "")
                        body = message.body.decode()
                        event = deserialize(event_type, body)
                        await self._publisher.publish(event)
                        logger.debug(
                            "rabbitmq_consumer.dispatched",
                            event_type=event_type,
                            queue=self._queue,
                        )
                    except Exception:
                        logger.exception(
                            "rabbitmq_consumer.dispatch_error",
                            queue=self._queue,
                        )
