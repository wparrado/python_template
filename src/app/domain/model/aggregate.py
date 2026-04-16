"""AggregateRoot base class.

Aggregate roots are the entry point for all operations within an aggregate.
They collect domain events and expose them for dispatch.
No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.events.base import DomainEvent
from app.domain.model.entity import Entity


@dataclass
class AggregateRoot(Entity):
    """Base class for all aggregate roots.

    Subclasses emit domain events via ``_record_event``.
    The application layer calls ``collect_events()`` after
    executing a use case and dispatches them.
    """

    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False, compare=False)

    def _record_event(self, event: DomainEvent) -> None:
        """Append a domain event to the internal queue."""
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Return and clear all pending domain events."""
        events = list(self._events)
        self._events.clear()
        return events
