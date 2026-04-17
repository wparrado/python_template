"""BrokerEventPublisher — abstract base for network-connected event publishers.

Extends ``IDomainEventPublisher`` with explicit lifecycle methods so the
application factory can open the connection on startup and close it gracefully
on shutdown.  Concrete adapters (RabbitMQ, Kafka, …) subclass this.
"""

from __future__ import annotations

from abc import abstractmethod

from app.domain.ports.outbound.event_publisher import IDomainEventPublisher


class BrokerEventPublisher(IDomainEventPublisher):
    """Base class for brokers that need a persistent connection.

    The application lifespan must call ``connect()`` before first use and
    ``disconnect()`` during graceful shutdown.  Implementations guarantee that
    ``publish()`` is a no-op (or raises loudly) when called without a live
    connection so misuse surfaces immediately in tests.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Open the connection to the broker and prepare resources."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Flush pending messages and close the connection gracefully."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return ``True`` when the adapter has an active broker connection."""
