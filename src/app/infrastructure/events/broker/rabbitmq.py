"""RabbitMQEventPublisher — domain event adapter using a topic exchange.

Publishes every domain event to a RabbitMQ **topic exchange** so that any
number of downstream consumers can bind queues to routing keys that match
their interests (e.g. ``ItemCreated``, ``Item.*``, ``#``).

Requirements
------------
Install the optional dependency::

    uv add aio-pika

Environment variables
---------------------
RABBITMQ_URL         amqp://guest:guest@localhost/   (default)
RABBITMQ_EXCHANGE    domain.events                   (default)

Message format
--------------
Each message body is the UTF-8 JSON payload produced by
``app.infrastructure.events.serialization.serialize``.  Headers carry:

- ``event_type``   — class name, e.g. ``ItemCreated``
- ``event_id``     — UUID of the event
- ``aggregate_id`` — UUID of the originating aggregate
- ``occurred_at``  — ISO-8601 timestamp

Routing key
-----------
``{event_type}`` — e.g. ``ItemCreated``

Binding examples (consumer side)
---------------------------------
- ``ItemCreated``       — only item-created events
- ``Item.*``            — all item events
- ``#``                 — every domain event on this exchange
"""

from __future__ import annotations

import structlog

from app.domain.events.base import DomainEvent
from app.infrastructure.events.broker.base import BrokerEventPublisher
from app.infrastructure.events.serialization import serialize

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class RabbitMQEventPublisher(BrokerEventPublisher):
    """Publishes domain events to a RabbitMQ topic exchange.

    Parameters
    ----------
    url:
        AMQP connection URL, e.g. ``amqp://guest:guest@localhost/``.
    exchange_name:
        Name of the topic exchange.  Created as ``durable=True`` if it does
        not already exist.
    """

    def __init__(self, url: str, exchange_name: str = "domain.events") -> None:
        """Store connection parameters — does NOT open a connection yet."""
        self._url = url
        self._exchange_name = exchange_name
        self._connection: object | None = None  # aio_pika.RobustConnection
        self._exchange: object | None = None  # aio_pika.Exchange

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open a robust connection and declare the topic exchange."""
        try:
            import aio_pika  # noqa: PLC0415 — optional dependency
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "aio-pika is required for RabbitMQ support. "
                "Install it with: uv add aio-pika"
            ) from exc

        self._connection = await aio_pika.connect_robust(self._url)
        channel = await self._connection.channel()  # type: ignore[union-attr]
        self._exchange = await channel.declare_exchange(
            self._exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        logger.info(
            "rabbitmq.connected",
            url=self._url,
            exchange=self._exchange_name,
        )

    async def disconnect(self) -> None:
        """Close the connection gracefully."""
        if self._connection is not None:
            await self._connection.close()  # type: ignore[union-attr]
            self._connection = None
            self._exchange = None
            logger.info("rabbitmq.disconnected")

    @property
    def is_connected(self) -> bool:
        """Return ``True`` when the connection is open."""
        return self._connection is not None

    # ------------------------------------------------------------------
    # IDomainEventPublisher
    # ------------------------------------------------------------------

    async def publish(self, event: DomainEvent) -> None:
        """Publish *event* to the topic exchange.

        Routing key = ``event_type`` (e.g. ``ItemCreated``).
        Body = UTF-8 JSON via ``serialize()``.
        """
        if self._exchange is None:
            raise RuntimeError(
                "RabbitMQEventPublisher is not connected. Call connect() first."
            )

        try:
            import aio_pika  # noqa: PLC0415 — optional dependency
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "aio-pika is required for RabbitMQ support."
            ) from exc

        body = serialize(event).encode()
        message = aio_pika.Message(
            body=body,
            content_type="application/json",
            headers={
                "event_type": event.event_type,
                "event_id": str(event.event_id),
                "aggregate_id": str(event.aggregate_id),
                "occurred_at": event.occurred_at.isoformat(),
            },
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(  # type: ignore[union-attr]
            message,
            routing_key=event.event_type,
        )
        logger.debug(
            "rabbitmq.published",
            event_type=event.event_type,
            event_id=str(event.event_id),
            routing_key=event.event_type,
            exchange=self._exchange_name,
        )
