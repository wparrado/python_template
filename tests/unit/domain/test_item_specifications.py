"""Unit tests for domain Item specifications."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.model.example.item import Item
from app.domain.specifications.item_specifications import (
    ActiveItemSpecification,
    AllItemsSpecification,
    NameContainsSpecification,
    PriceInRangeSpecification,
)


@pytest.fixture
def active_item() -> Item:
    return Item.create(name="Widget", price=Decimal("9.99"), description="A widget")


@pytest.fixture
def deleted_item() -> Item:
    item = Item.create(name="Old Item", price=Decimal("1.00"))
    item.mark_deleted()
    return item


# ---------------------------------------------------------------------------
# AllItemsSpecification
# ---------------------------------------------------------------------------


def test_all_items_spec_always_true(active_item: Item, deleted_item: Item) -> None:
    spec = AllItemsSpecification()
    assert spec.is_satisfied_by(active_item)
    assert spec.is_satisfied_by(deleted_item)


# ---------------------------------------------------------------------------
# ActiveItemSpecification
# ---------------------------------------------------------------------------


def test_active_spec_matches_active_item(active_item: Item) -> None:
    assert ActiveItemSpecification().is_satisfied_by(active_item)


def test_active_spec_rejects_deleted_item(deleted_item: Item) -> None:
    assert not ActiveItemSpecification().is_satisfied_by(deleted_item)


# ---------------------------------------------------------------------------
# PriceInRangeSpecification
# ---------------------------------------------------------------------------


def test_price_range_both_bounds(active_item: Item) -> None:
    assert PriceInRangeSpecification(Decimal("5"), Decimal("15")).is_satisfied_by(active_item)
    assert not PriceInRangeSpecification(Decimal("10"), Decimal("20")).is_satisfied_by(active_item)


def test_price_range_only_min(active_item: Item) -> None:
    assert PriceInRangeSpecification(min_price=Decimal("5")).is_satisfied_by(active_item)
    assert not PriceInRangeSpecification(min_price=Decimal("10")).is_satisfied_by(active_item)


def test_price_range_only_max(active_item: Item) -> None:
    assert PriceInRangeSpecification(max_price=Decimal("10")).is_satisfied_by(active_item)
    assert not PriceInRangeSpecification(max_price=Decimal("5")).is_satisfied_by(active_item)


def test_price_range_no_bounds_matches_all(active_item: Item) -> None:
    assert PriceInRangeSpecification().is_satisfied_by(active_item)


# ---------------------------------------------------------------------------
# NameContainsSpecification
# ---------------------------------------------------------------------------


def test_name_contains_case_insensitive(active_item: Item) -> None:
    assert NameContainsSpecification("WIDGET").is_satisfied_by(active_item)
    assert NameContainsSpecification("widget").is_satisfied_by(active_item)
    assert NameContainsSpecification("idg").is_satisfied_by(active_item)


def test_name_contains_no_match(active_item: Item) -> None:
    assert not NameContainsSpecification("gadget").is_satisfied_by(active_item)


# ---------------------------------------------------------------------------
# Composite specifications
# ---------------------------------------------------------------------------


def test_and_spec_both_satisfied(active_item: Item) -> None:
    spec = ActiveItemSpecification() & PriceInRangeSpecification(max_price=Decimal("15"))
    assert spec.is_satisfied_by(active_item)


def test_and_spec_one_fails(active_item: Item) -> None:
    spec = ActiveItemSpecification() & PriceInRangeSpecification(max_price=Decimal("1"))
    assert not spec.is_satisfied_by(active_item)


def test_or_spec_one_satisfied(deleted_item: Item) -> None:
    spec = ActiveItemSpecification() | NameContainsSpecification("old")
    assert spec.is_satisfied_by(deleted_item)


def test_or_spec_none_satisfied(active_item: Item) -> None:
    spec = NameContainsSpecification("xyz") | PriceInRangeSpecification(max_price=Decimal("1"))
    assert not spec.is_satisfied_by(active_item)


def test_not_spec_inverts(active_item: Item) -> None:
    assert not (~ActiveItemSpecification()).is_satisfied_by(active_item)


def test_not_active_matches_deleted(deleted_item: Item) -> None:
    spec = ~ActiveItemSpecification()
    assert spec.is_satisfied_by(deleted_item)


def test_complex_composition(active_item: Item) -> None:
    spec = (
        ActiveItemSpecification()
        & NameContainsSpecification("widget")
        & PriceInRangeSpecification(min_price=Decimal("5"), max_price=Decimal("15"))
    )
    assert spec.is_satisfied_by(active_item)
