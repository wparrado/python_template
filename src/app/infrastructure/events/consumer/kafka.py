"""KafkaEventConsumer — consumes domain events from Kafka topics.

This adapter subscribes to one or more Kafka topics and dispatches received
events to the in-process publisher.

Typical use-case
----------------
A *second service* (e.g. Search indexer) runs this consumer::

    consumer = KafkaEventConsumer(
        bootstrap_servers="kafka:9092",
        topics=["app.ItemCreated", "app.ItemUpdated"],
        group_id="search-indexer",
        publisher=in_process_publisher,
    )
    await consumer.start()

Requirements
------------
    uv add aiokafka

Delivery semantics
------------------
- Offsets are committed **after** successful dispatch (at-least-once).
- Use an idempotent consumer-side design or a processed-event store to
  handle duplicate deliveries safely.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

try:
    from aiokafka import AIOKafkaConsumer
except ImportError:
    AIOKafkaConsumer = None

from app.infrastructure.events.consumer.base import BrokerEventConsumer
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.events.serialization import deserialize

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class KafkaEventConsumer(BrokerEventConsumer):
    """Consumes domain events from Kafka topics.

    Parameters
    ----------
    bootstrap_servers:
        Comma-separated Kafka brokers.
    topics:
        List of fully-qualified topic names to subscribe to.
        E.g. ``["app.ItemCreated", "app.ItemUpdated"]`` or ``["app.*"]``
        if broker supports wildcards.
    group_id:
        Consumer group ID.  Use a unique name per logical consumer so each
        service maintains its own independent offset.
    publisher:
        In-process publisher to dispatch deserialized events to.
    auto_offset_reset:
        ``"earliest"`` replays all events from the beginning (useful for
        new consumers / replay).  ``"latest"`` (default) skips past events.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topics: list[str],
        group_id: str,
        publisher: InProcessEventPublisher,
        auto_offset_reset: str = "latest",
    ) -> None:
        """Store configuration — does NOT connect yet."""
        self._bootstrap_servers = bootstrap_servers
        self._topics = topics
        self._group_id = group_id
        self._publisher = publisher
        self._auto_offset_reset = auto_offset_reset
        self._consumer: Any | None = None
        self._task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # BrokerEventConsumer
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the Kafka consumer and begin polling in a background task."""
        if AIOKafkaConsumer is None:
            raise ImportError("aiokafka is required. Install with: uv add aiokafka")

        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset=self._auto_offset_reset,
            enable_auto_commit=False,  # manual commit after dispatch
            value_deserializer=lambda v: v.decode(),
        )
        await self._consumer.start()
        self._task = asyncio.create_task(self._poll(), name=f"consumer.kafka.{self._group_id}")
        logger.info(
            "kafka_consumer.started",
            topics=self._topics,
            group_id=self._group_id,
        )

    async def stop(self) -> None:
        """Stop polling and commit final offsets."""
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        logger.info("kafka_consumer.stopped", group_id=self._group_id)

    @property
    def is_running(self) -> bool:
        """Return True when the consumer poll task is active."""
        return self._task is not None and not self._task.done()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _poll(self) -> None:
        """Main poll loop — commit offset after each successful dispatch."""
        if self._consumer is None:
            return
        async for msg in self._consumer:
            try:
                # Header lookup: headers is a list of (key, bytes) tuples
                headers = dict(msg.headers)
                event_type = headers.get("event_type", b"").decode()
                event = deserialize(event_type, msg.value)
                await self._publisher.publish(event)
                await self._consumer.commit()
                logger.debug(
                    "kafka_consumer.dispatched",
                    event_type=event_type,
                    topic=msg.topic,
                    offset=msg.offset,
                )
            except Exception:
                logger.exception(
                    "kafka_consumer.dispatch_error",
                    topic=msg.topic,
                    offset=msg.offset,
                )
