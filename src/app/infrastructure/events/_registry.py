"""Event registry — maps event type names to their domain classes.

Used by the outbox deserializer to reconstruct typed DomainEvent instances
from the JSON stored in the outbox table.  Add new event classes here as
the domain model grows.
"""

from __future__ import annotations

from app.domain.events.base import DomainEvent
from app.domain.model.example.item_events import ItemCreated, ItemDeleted, ItemUpdated

EVENT_REGISTRY: dict[str, type[DomainEvent]] = {
    "ItemCreated": ItemCreated,
    "ItemUpdated": ItemUpdated,
    "ItemDeleted": ItemDeleted,
}
