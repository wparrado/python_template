"""Property-based tests for the Item domain model.

Uses Hypothesis to generate arbitrary valid/invalid inputs and verify
that domain invariants hold for all inputs, not just hand-picked examples.

Strategies
----------
- ``valid_item_names``: non-empty stripped strings (≤200 chars)
- ``valid_prices``: non-negative decimals with 2 decimal places
- ``invalid_prices``: strictly negative decimals
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.example.item import Item
from app.domain.specifications.item_specifications import (
    ActiveItemSpecification,
    AllItemsSpecification,
    NameContainsSpecification,
    PriceInRangeSpecification,
)

# ---------------------------------------------------------------------------
# Custom strategies
# ---------------------------------------------------------------------------

valid_item_names = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != "")

valid_prices = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("999999.99"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)

negative_prices = st.decimals(
    max_value=Decimal("-0.01"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)


# ---------------------------------------------------------------------------
# Item.create invariants
# ---------------------------------------------------------------------------


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=100)
def test_valid_item_always_creates(name: str, price: Decimal) -> None:
    """Any valid name and non-negative price must succeed."""
    item = Item.create(name=name, price=price)
    assert item.name.value == name.strip()
    assert item.price.amount == price
    assert not item.is_deleted


@given(price=negative_prices)
@settings(max_examples=50)
def test_negative_price_always_raises(price: Decimal) -> None:
    """Any negative price must raise ValidationError."""
    with pytest.raises(ValidationError):
        Item.create(name="Valid Name", price=price)


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=50)
def test_collect_events_clears_after_first_call(name: str, price: Decimal) -> None:
    """collect_events() must drain the queue so a second call always returns []."""
    item = Item.create(name=name, price=price)
    item.collect_events()
    assert item.collect_events() == []


# ---------------------------------------------------------------------------
# AllItemsSpecification — always True
# ---------------------------------------------------------------------------


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=50)
def test_all_items_spec_always_true_property(name: str, price: Decimal) -> None:
    item = Item.create(name=name, price=price)
    assert AllItemsSpecification().is_satisfied_by(item)


# ---------------------------------------------------------------------------
# ActiveItemSpecification
# ---------------------------------------------------------------------------


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=50)
def test_active_spec_always_true_before_deletion(name: str, price: Decimal) -> None:
    item = Item.create(name=name, price=price)
    assert ActiveItemSpecification().is_satisfied_by(item)


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=50)
def test_active_spec_always_false_after_deletion(name: str, price: Decimal) -> None:
    item = Item.create(name=name, price=price)
    item.mark_deleted()
    assert not ActiveItemSpecification().is_satisfied_by(item)


# ---------------------------------------------------------------------------
# PriceInRangeSpecification
# ---------------------------------------------------------------------------


@given(price=valid_prices)
@settings(max_examples=50)
def test_price_in_range_no_bounds_always_matches(price: Decimal) -> None:
    item = Item.create(name="Widget", price=price)
    assert PriceInRangeSpecification().is_satisfied_by(item)


@given(price=valid_prices)
@settings(max_examples=50)
def test_price_in_range_exact_min_matches(price: Decimal) -> None:
    item = Item.create(name="Widget", price=price)
    assert PriceInRangeSpecification(min_price=price).is_satisfied_by(item)


@given(price=valid_prices)
@settings(max_examples=50)
def test_price_in_range_exact_max_matches(price: Decimal) -> None:
    item = Item.create(name="Widget", price=price)
    assert PriceInRangeSpecification(max_price=price).is_satisfied_by(item)


# ---------------------------------------------------------------------------
# NameContainsSpecification
# ---------------------------------------------------------------------------


@given(name=valid_item_names)
@settings(max_examples=50)
def test_name_contains_full_name_always_matches(name: str) -> None:
    item = Item.create(name=name, price=Decimal("1.00"))
    assert NameContainsSpecification(name.strip().lower()).is_satisfied_by(item)


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=50)
def test_empty_keyword_always_matches(name: str, price: Decimal) -> None:
    """An empty keyword matches every item name (substring of any string)."""
    item = Item.create(name=name, price=price)
    assert NameContainsSpecification("").is_satisfied_by(item)


# ---------------------------------------------------------------------------
# Composition: And / Or / Not laws
# ---------------------------------------------------------------------------


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=50)
def test_not_not_is_identity(name: str, price: Decimal) -> None:
    """¬¬P ≡ P for ActiveItemSpecification."""
    item = Item.create(name=name, price=price)
    spec = ActiveItemSpecification()
    double_negated = ~(~spec)
    assert double_negated.is_satisfied_by(item) == spec.is_satisfied_by(item)


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=50)
def test_and_commutative(name: str, price: Decimal) -> None:
    """A & B ≡ B & A."""
    item = Item.create(name=name, price=price)
    a = ActiveItemSpecification()
    b = PriceInRangeSpecification(max_price=Decimal("999999.99"))
    assert (a & b).is_satisfied_by(item) == (b & a).is_satisfied_by(item)


@given(name=valid_item_names, price=valid_prices)
@settings(max_examples=50)
def test_or_commutative(name: str, price: Decimal) -> None:
    """A | B ≡ B | A."""
    item = Item.create(name=name, price=price)
    a = ActiveItemSpecification()
    b = AllItemsSpecification()
    assert (a | b).is_satisfied_by(item) == (b | a).is_satisfied_by(item)
