"""KafkaEventPublisher — domain event adapter using per-event topics.

Publishes every domain event to a dedicated Kafka topic so consumers can
subscribe to exactly the event types they care about.

Requirements
------------
Install the optional dependency::

    uv add aiokafka

Environment variables
---------------------
KAFKA_BOOTSTRAP_SERVERS   localhost:9092    (default)
KAFKA_TOPIC_PREFIX        app               (default)

Message format
--------------
Each Kafka record:

- **Key**   — UTF-8 ``aggregate_id`` (UUID string) — enables log-compaction
  and guarantees ordering within a partition for the same aggregate.
- **Value** — UTF-8 JSON payload from ``serialize()``.
- **Headers** — ``event_type``, ``event_id``, ``aggregate_id``, ``occurred_at``.

Topic naming
------------
``{prefix}.{event_type}`` — e.g. ``app.ItemCreated``

Set ``KAFKA_TOPIC_PREFIX`` to scope topics per environment or team.

Delivery semantics
------------------
``acks="all"`` (default) — the producer waits for all in-sync replicas to
acknowledge before considering the message sent.  Combined with the Outbox
Pattern this provides **at-least-once** delivery.
"""

from __future__ import annotations

import structlog

from app.domain.events.base import DomainEvent
from app.infrastructure.events.broker.base import BrokerEventPublisher
from app.infrastructure.events.serialization import serialize

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class KafkaEventPublisher(BrokerEventPublisher):
    """Publishes domain events to dedicated Kafka topics.

    Parameters
    ----------
    bootstrap_servers:
        Comma-separated broker addresses, e.g. ``localhost:9092``.
    topic_prefix:
        Prepended to the event class name to form the topic.
        E.g. prefix ``"app"`` → topic ``"app.ItemCreated"``.
    acks:
        Producer acknowledgement level.  Defaults to ``"all"`` for durability.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic_prefix: str = "app",
        acks: str = "all",
    ) -> None:
        """Store configuration — does NOT open a connection yet."""
        self._bootstrap_servers = bootstrap_servers
        self._topic_prefix = topic_prefix
        self._acks = acks
        self._producer: object | None = None  # aiokafka.AIOKafkaProducer

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create and start the Kafka producer."""
        try:
            from aiokafka import AIOKafkaProducer  # noqa: PLC0415 — optional dependency
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "aiokafka is required for Kafka support. "
                "Install it with: uv add aiokafka"
            ) from exc

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            acks=self._acks,
            value_serializer=lambda v: v.encode() if isinstance(v, str) else v,
            key_serializer=lambda k: k.encode() if isinstance(k, str) else k,
        )
        await self._producer.start()  # type: ignore[union-attr]
        logger.info(
            "kafka.connected",
            bootstrap_servers=self._bootstrap_servers,
            topic_prefix=self._topic_prefix,
        )

    async def disconnect(self) -> None:
        """Flush and stop the Kafka producer."""
        if self._producer is not None:
            await self._producer.stop()  # type: ignore[union-attr]
            self._producer = None
            logger.info("kafka.disconnected")

    @property
    def is_connected(self) -> bool:
        """Return ``True`` when the producer is running."""
        return self._producer is not None

    # ------------------------------------------------------------------
    # IDomainEventPublisher
    # ------------------------------------------------------------------

    async def publish(self, event: DomainEvent) -> None:
        """Publish *event* to its dedicated Kafka topic.

        Topic   = ``{prefix}.{event_type}``  (e.g. ``app.ItemCreated``)
        Key     = ``str(aggregate_id)``
        Value   = UTF-8 JSON via ``serialize()``
        Headers = [(name, bytes), …] with event metadata
        """
        if self._producer is None:
            raise RuntimeError(
                "KafkaEventPublisher is not connected. Call connect() first."
            )

        topic = f"{self._topic_prefix}.{event.event_type}"
        headers = [
            ("event_type", event.event_type.encode()),
            ("event_id", str(event.event_id).encode()),
            ("aggregate_id", str(event.aggregate_id).encode()),
            ("occurred_at", event.occurred_at.isoformat().encode()),
        ]
        await self._producer.send_and_wait(  # type: ignore[union-attr]
            topic=topic,
            key=str(event.aggregate_id),
            value=serialize(event),
            headers=headers,
        )
        logger.debug(
            "kafka.published",
            event_type=event.event_type,
            event_id=str(event.event_id),
            topic=topic,
            aggregate_id=str(event.aggregate_id),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def topic_for(self, event_type: str) -> str:
        """Return the fully-qualified topic name for an event type."""
        return f"{self._topic_prefix}.{event_type}"
