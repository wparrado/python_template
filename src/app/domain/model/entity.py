"""Entity base class.

Entities have identity (UUID) and are compared by id.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Entity:
    """Base class for all domain entities.

    Identity is defined by ``id``, not attribute values.
    ``is_deleted`` is set to ``True`` by lifecycle methods (e.g.,
    ``mark_deleted``) to indicate soft-deleted state before the aggregate
    is removed from the repository.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_deleted: bool = field(default=False, init=False, repr=True, compare=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)
