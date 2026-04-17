"""Unit tests for the Category domain aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.example.category import Category
from app.domain.model.example.category_events import CategoryCreated, CategoryDeleted, CategoryUpdated
from app.domain.model.example.category_value_objects import CategoryName, CategorySlug
from app.infrastructure.clock.fake_clock import FakeClock


def test_create_category_emits_created_event() -> None:
    category = Category.create(name="Electronics", description="Devices")
    events = category.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], CategoryCreated)
    assert events[0].name == "Electronics"
    assert events[0].slug == "electronics"


def test_create_category_derives_slug_from_name() -> None:
    category = Category.create(name="Home & Garden")
    assert category.slug.value == "home-garden"


def test_create_category_with_explicit_slug() -> None:
    category = Category.create(name="Electronics", slug="my-electronics")
    assert category.slug.value == "my-electronics"


def test_create_category_empty_name_raises() -> None:
    with pytest.raises(ValidationError):
        Category.create(name="")


def test_create_category_name_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        Category.create(name="x" * 101)


def test_create_category_invalid_slug_raises() -> None:
    with pytest.raises(ValidationError):
        Category.create(name="Electronics", slug="Invalid Slug!")


def test_create_category_description_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        Category.create(name="Electronics", description="x" * 501)


def test_update_category_emits_updated_event() -> None:
    clock = FakeClock(datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC))
    category = Category.create(name="Electronics", clock=clock)
    category.collect_events()  # clear creation event
    category.update(name="Consumer Electronics", clock=clock)
    events = category.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], CategoryUpdated)
    assert events[0].name == "Consumer Electronics"


def test_update_name_re_derives_slug() -> None:
    clock = FakeClock(datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC))
    category = Category.create(name="Electronics", clock=clock)
    category.collect_events()
    category.update(name="Home Appliances", clock=clock)
    assert category.slug.value == "home-appliances"


def test_update_name_with_explicit_slug_keeps_slug() -> None:
    clock = FakeClock(datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC))
    category = Category.create(name="Electronics", clock=clock)
    category.collect_events()
    category.update(name="Gadgets", slug="tech-gadgets", clock=clock)
    assert category.slug.value == "tech-gadgets"


def test_update_category_invalid_name_raises() -> None:
    clock = FakeClock(datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC))
    category = Category.create(name="Electronics", clock=clock)
    with pytest.raises(ValidationError):
        category.update(name="", clock=clock)


def test_collect_events_clears_queue() -> None:
    category = Category.create(name="Electronics")
    category.collect_events()
    assert category.collect_events() == []


def test_mark_deleted_sets_flag() -> None:
    category = Category.create(name="Electronics")
    assert not category.is_deleted
    category.mark_deleted()
    assert category.is_deleted


def test_mark_deleted_emits_event() -> None:
    category = Category.create(name="Electronics")
    category.collect_events()
    category.mark_deleted()
    events = category.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], CategoryDeleted)
    assert events[0].category_id == category.id


def test_category_name_strips_whitespace() -> None:
    name = CategoryName("  Electronics  ")
    assert name.value == "Electronics"


def test_category_slug_validates_format() -> None:
    slug = CategorySlug("valid-slug-123")
    assert slug.value == "valid-slug-123"
    with pytest.raises(ValidationError):
        CategorySlug("Invalid Slug")
    with pytest.raises(ValidationError):
        CategorySlug("UPPERCASE")


# ---------------------------------------------------------------------------
# IClock / FakeClock — deterministic time control
# ---------------------------------------------------------------------------


def test_update_category_uses_clock() -> None:
    """Category.update() must advance updated_at to the clock's current time."""
    t0 = datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC)
    clock = FakeClock(t0)
    category = Category.create(name="Electronics")

    clock.tick(timedelta(days=1))
    category.update(name="Consumer Electronics", clock=clock)

    assert category.updated_at == datetime(2024, 3, 11, 9, 0, 0, tzinfo=UTC)


def test_update_category_with_fake_clock_is_deterministic() -> None:
    """update() with FakeClock must use exactly the clock's timestamp."""
    t0 = datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC)
    clock = FakeClock(t0)
    category = Category.create(name="Electronics", clock=clock)
    clock.tick(timedelta(days=1))
    category.update(name="Updated", clock=clock)
    assert category.updated_at == datetime(2024, 3, 11, 9, 0, 0, tzinfo=UTC)
