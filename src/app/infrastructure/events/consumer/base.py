"""BrokerEventConsumer — abstract base for event consumer adapters.

Mirrors ``BrokerEventPublisher`` on the inbound side.  A consumer listens on
a broker queue/topic, deserializes messages, and dispatches them to the
registered in-process handler so the application layer can react to events
produced by *other* services.

Usage (example, called from an application lifespan)::

    consumer = RabbitMQEventConsumer(
        url=settings.rabbitmq_url,
        exchange=settings.rabbitmq_exchange,
        queue="notifications.items",
        routing_keys=["ItemCreated", "ItemUpdated"],
        publisher=in_process_publisher,
    )
    await consumer.start()   # begins consuming in the background
    # … application runs …
    await consumer.stop()    # drains and disconnects
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BrokerEventConsumer(ABC):
    """Abstract base for adapters that consume domain events from a broker.

    Implementations must be safe to call ``start()`` and ``stop()`` from the
    application lifespan without blocking the event loop.
    """

    @abstractmethod
    async def start(self) -> None:
        """Connect to the broker and begin consuming messages in the background."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop consuming, drain in-flight messages, and disconnect cleanly."""

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Return ``True`` when the consumer background task is active."""
