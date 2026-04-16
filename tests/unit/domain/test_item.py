"""Unit tests for the Item domain aggregate."""

from __future__ import annotations

import pytest

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.example.item import Item
from app.domain.model.example.item_events import ItemCreated, ItemUpdated


def test_create_item_emits_created_event() -> None:
    item = Item.create(name="Widget", price=9.99, description="Desc")
    events = item.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], ItemCreated)
    assert events[0].name == "Widget"


def test_create_item_empty_name_raises() -> None:
    with pytest.raises(ValidationError):
        Item.create(name="", price=9.99)


def test_create_item_negative_price_raises() -> None:
    with pytest.raises(ValidationError):
        Item.create(name="Widget", price=-1.0)


def test_update_item_emits_updated_event() -> None:
    item = Item.create(name="Widget", price=9.99)
    item.collect_events()  # clear creation event
    item.update(name="Updated Widget", price=19.99)
    events = item.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], ItemUpdated)
    assert events[0].name == "Updated Widget"


def test_update_item_invalid_price_raises() -> None:
    item = Item.create(name="Widget", price=9.99)
    with pytest.raises(ValidationError):
        item.update(price=-5.0)


def test_collect_events_clears_queue() -> None:
    item = Item.create(name="Widget", price=1.0)
    item.collect_events()
    assert item.collect_events() == []
