"""In-process domain event publisher (secondary adapter).

Dispatches domain events synchronously to registered handlers.
In production, replace with an async message broker adapter
(RabbitMQ, Kafka, AWS SNS, etc.) that implements IDomainEventPublisher.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.domain.events.base import DomainEvent
from app.domain.ports.outbound.event_publisher import IDomainEventPublisher

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class InProcessEventPublisher(IDomainEventPublisher):
    """Dispatches events to in-process async handlers."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Dispatch the event to all registered handlers for its type."""
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            await handler(event)
