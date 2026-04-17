"""Unit tests for the events infrastructure layer.

Covers:
- InProcessEventPublisher: subscribe/publish dispatch
- serialize / deserialize round-trip for all registered event types
- EVENT_REGISTRY: correct mapping of event type names to classes
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.events.base import DomainEvent
from app.domain.model.example.item_events import ItemCreated, ItemDeleted, ItemUpdated
from app.infrastructure.events._registry import EVENT_REGISTRY
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.events.serialization import deserialize, serialize

# ---------------------------------------------------------------------------
# InProcessEventPublisher
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_dispatches_to_subscriber() -> None:
    publisher = InProcessEventPublisher()
    received: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    event = ItemCreated(aggregate_id=uuid.uuid4(), name="Widget", price=Decimal("9.99"))
    publisher.subscribe(ItemCreated, handler)
    await publisher.publish(event)

    assert len(received) == 1
    assert received[0] is event


@pytest.mark.asyncio
async def test_publish_dispatches_to_multiple_subscribers() -> None:
    publisher = InProcessEventPublisher()
    call_count = 0

    async def handler(_: DomainEvent) -> None:
        nonlocal call_count
        call_count += 1

    event = ItemCreated(aggregate_id=uuid.uuid4(), name="Widget", price=Decimal("1.00"))
    publisher.subscribe(ItemCreated, handler)
    publisher.subscribe(ItemCreated, handler)
    await publisher.publish(event)

    assert call_count == 2


@pytest.mark.asyncio
async def test_publish_only_dispatches_matching_type() -> None:
    publisher = InProcessEventPublisher()
    received: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    publisher.subscribe(ItemCreated, handler)
    await publisher.publish(ItemDeleted(aggregate_id=uuid.uuid4(), item_id=uuid.uuid4()))

    assert received == []


@pytest.mark.asyncio
async def test_publish_with_no_subscribers_is_noop() -> None:
    publisher = InProcessEventPublisher()
    event = ItemCreated(aggregate_id=uuid.uuid4(), name="Widget", price=Decimal("1.00"))
    await publisher.publish(event)  # must not raise


@pytest.mark.asyncio
async def test_subscribe_different_event_types() -> None:
    publisher = InProcessEventPublisher()
    created_events: list[DomainEvent] = []
    deleted_events: list[DomainEvent] = []

    async def on_created(e: DomainEvent) -> None:
        created_events.append(e)

    async def on_deleted(e: DomainEvent) -> None:
        deleted_events.append(e)

    publisher.subscribe(ItemCreated, on_created)
    publisher.subscribe(ItemDeleted, on_deleted)

    agg_id = uuid.uuid4()
    await publisher.publish(ItemCreated(aggregate_id=agg_id, name="X", price=Decimal("1")))
    await publisher.publish(ItemDeleted(aggregate_id=agg_id, item_id=agg_id))

    assert len(created_events) == 1
    assert len(deleted_events) == 1


# ---------------------------------------------------------------------------
# Serialization / Deserialization round-trips
# ---------------------------------------------------------------------------


def test_serialize_item_created() -> None:
    agg_id = uuid.uuid4()
    event = ItemCreated(aggregate_id=agg_id, name="Widget", price=Decimal("19.99"), description="Desc")
    payload = serialize(event)
    assert '"name": "Widget"' in payload
    assert str(agg_id) in payload


def test_deserialize_item_created_round_trip() -> None:
    agg_id = uuid.uuid4()
    event_id = uuid.uuid4()
    occurred_at = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    original = ItemCreated(
        aggregate_id=agg_id,
        event_id=event_id,
        occurred_at=occurred_at,
        name="Round-trip Widget",
        price=Decimal("42.00"),
        description="Test",
    )
    payload = serialize(original)
    restored = deserialize("ItemCreated", payload)

    assert isinstance(restored, ItemCreated)
    assert restored.aggregate_id == agg_id
    assert restored.event_id == event_id
    assert restored.occurred_at == occurred_at
    assert restored.name == "Round-trip Widget"
    assert restored.price == Decimal("42.00")
    assert restored.description == "Test"


def test_deserialize_item_updated_round_trip() -> None:
    original = ItemUpdated(
        aggregate_id=uuid.uuid4(),
        name="Updated",
        price=Decimal("5.00"),
        description=None,
    )
    restored = deserialize("ItemUpdated", serialize(original))
    assert isinstance(restored, ItemUpdated)
    assert restored.name == "Updated"
    assert restored.price == Decimal("5.00")
    assert restored.description is None


def test_deserialize_item_deleted_round_trip() -> None:
    item_id = uuid.uuid4()
    original = ItemDeleted(aggregate_id=uuid.uuid4(), item_id=item_id)
    restored = deserialize("ItemDeleted", serialize(original))
    assert isinstance(restored, ItemDeleted)
    assert restored.item_id == item_id


def test_deserialize_unknown_event_type_raises() -> None:
    with pytest.raises(KeyError):
        deserialize("NonExistentEvent", '{"aggregate_id": "00000000-0000-0000-0000-000000000000"}')


# ---------------------------------------------------------------------------
# EVENT_REGISTRY
# ---------------------------------------------------------------------------


def test_registry_contains_all_item_events() -> None:
    assert "ItemCreated" in EVENT_REGISTRY
    assert "ItemUpdated" in EVENT_REGISTRY
    assert "ItemDeleted" in EVENT_REGISTRY


def test_registry_maps_to_correct_classes() -> None:
    assert EVENT_REGISTRY["ItemCreated"] is ItemCreated
    assert EVENT_REGISTRY["ItemUpdated"] is ItemUpdated
    assert EVENT_REGISTRY["ItemDeleted"] is ItemDeleted
