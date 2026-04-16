"""Outbound port: IDomainEventPublisher.

The application layer depends on this interface to dispatch domain events.
Infrastructure adapters implement it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.events.base import DomainEvent


class IDomainEventPublisher(ABC):
    """Secondary (driven) port for publishing domain events."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a single domain event."""
        ...

    async def publish_all(self, events: list[DomainEvent]) -> None:
        """Convenience: publish a list of events."""
        for event in events:
            await self.publish(event)
