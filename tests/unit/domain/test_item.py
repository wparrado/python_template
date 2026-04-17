"""Unit tests for the Item domain aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.example.item import Item
from app.domain.model.example.item_events import ItemCreated, ItemUpdated
from app.infrastructure.clock.fake_clock import FakeClock


def test_create_item_emits_created_event() -> None:
    item = Item.create(name="Widget", price=Decimal("9.99"), description="Desc")
    events = item.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], ItemCreated)
    assert events[0].name == "Widget"


def test_create_item_empty_name_raises() -> None:
    with pytest.raises(ValidationError):
        Item.create(name="", price=Decimal("9.99"))


def test_create_item_negative_price_raises() -> None:
    with pytest.raises(ValidationError):
        Item.create(name="Widget", price=Decimal("-1.00"))


def test_update_item_emits_updated_event() -> None:
    clock = FakeClock(datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC))
    item = Item.create(name="Widget", price=Decimal("9.99"), clock=clock)
    item.collect_events()  # clear creation event
    item.update(name="Updated Widget", price=Decimal("19.99"), clock=clock)
    events = item.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], ItemUpdated)
    assert events[0].name == "Updated Widget"


def test_update_item_invalid_price_raises() -> None:
    clock = FakeClock(datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC))
    item = Item.create(name="Widget", price=Decimal("9.99"), clock=clock)
    with pytest.raises(ValidationError):
        item.update(price=Decimal("-5.00"), clock=clock)


def test_collect_events_clears_queue() -> None:
    item = Item.create(name="Widget", price=Decimal("1.00"))
    item.collect_events()
    assert item.collect_events() == []


def test_mark_deleted_sets_flag() -> None:
    item = Item.create(name="Widget", price=Decimal("1.00"))
    assert not item.is_deleted
    item.mark_deleted()
    assert item.is_deleted


# ---------------------------------------------------------------------------
# IClock / FakeClock — deterministic time control
# ---------------------------------------------------------------------------


def test_create_item_uses_clock() -> None:
    """Item.create() must use the injected clock for created_at and updated_at."""
    fixed = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    clock = FakeClock(fixed)
    item = Item.create(name="Widget", price=Decimal("9.99"), clock=clock)
    assert item.created_at == fixed
    assert item.updated_at == fixed


def test_update_item_uses_clock() -> None:
    """Item.update() must advance updated_at to the clock's current time."""
    t0 = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    clock = FakeClock(t0)
    item = Item.create(name="Widget", price=Decimal("9.99"), clock=clock)

    clock.tick(timedelta(hours=1))
    item.update(name="Updated Widget", clock=clock)

    assert item.created_at == t0
    assert item.updated_at == datetime(2024, 1, 15, 13, 0, 0, tzinfo=UTC)


def test_create_without_clock_uses_fake_clock() -> None:
    """Creating with FakeClock must use the fixed timestamp."""
    fixed = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)
    clock = FakeClock(fixed)
    item = Item.create(name="Widget", price=Decimal("9.99"), clock=clock)
    assert item.created_at == fixed
    assert item.updated_at == fixed


def test_fake_clock_tick_is_cumulative() -> None:
    """Multiple tick() calls must accumulate correctly."""
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    clock = FakeClock(t0)
    clock.tick(timedelta(hours=1))
    clock.tick(timedelta(minutes=30))
    assert clock.now() == datetime(2024, 1, 1, 1, 30, tzinfo=UTC)
