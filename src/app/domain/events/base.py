"""Base DomainEvent dataclass.

Domain events are emitted by aggregate roots to communicate
that something meaningful happened in the domain.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class DomainEvent:
    """Immutable record of something that happened in the domain."""

    aggregate_id: uuid.UUID
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return self.__class__.__name__
