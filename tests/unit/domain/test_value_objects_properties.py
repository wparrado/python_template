"""Property-based tests for Item domain Value Objects.

Uses Hypothesis to verify that each Value Object's invariants hold for
arbitrary inputs — complementing the example-based tests in test_item.py.

Value Objects under test
------------------------
- ItemName   : non-empty, whitespace-stripped string
- Money      : non-negative Decimal amount
- Description: optional free-text (any string, defaults to "")
- CategoryId : UUID wrapper (any valid UUID)
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.example.value_objects import CategoryId, Description, ItemName, Money

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Non-empty strings that have at least one non-whitespace character
non_empty_printable = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip() != "")

# Strings that are either empty or consist only of characters Python's str.strip()
# removes: space, tab, newline, carriage-return, vertical-tab, form-feed.
# Building from these characters guarantees s.strip() == "" without any filter.
whitespace_only = st.text(
    alphabet=st.sampled_from([" ", "\t", "\n", "\r", "\x0b", "\x0c"]),
    min_size=0,
    max_size=50,
)

non_negative_decimals = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("999999.99"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)

negative_decimals = st.decimals(
    max_value=Decimal("-0.01"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)

any_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    max_size=500,
)

# ---------------------------------------------------------------------------
# ItemName
# ---------------------------------------------------------------------------


@given(name=non_empty_printable)
@settings(max_examples=100)
def test_item_name_accepts_any_non_empty_stripped_string(name: str) -> None:
    """Any string with at least one non-whitespace character must be accepted."""
    vo = ItemName(name)
    assert vo.value == name.strip()
    assert vo.value != ""


@given(name=non_empty_printable)
@settings(max_examples=100)
def test_item_name_is_always_stripped(name: str) -> None:
    """ItemName must always store the stripped value regardless of leading/trailing spaces."""
    padded = f"  {name}  "
    vo = ItemName(padded)
    assert vo.value == padded.strip()


@given(name=whitespace_only)
@settings(max_examples=50)
def test_item_name_rejects_whitespace_only(name: str) -> None:
    """Whitespace-only or empty strings must raise ValidationError."""
    with pytest.raises(ValidationError):
        ItemName(name)


@given(a=non_empty_printable, b=non_empty_printable)
@settings(max_examples=50)
def test_item_name_equality_by_value(a: str, b: str) -> None:
    """Two ItemName instances with the same stripped value must be equal."""
    if a.strip() == b.strip():
        assert ItemName(a) == ItemName(b)
    else:
        assert ItemName(a) != ItemName(b)


@given(name=non_empty_printable)
@settings(max_examples=50)
def test_item_name_str_returns_value(name: str) -> None:
    """str(ItemName) must equal its stored value."""
    vo = ItemName(name)
    assert str(vo) == vo.value


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------


@given(amount=non_negative_decimals)
@settings(max_examples=100)
def test_money_accepts_non_negative(amount: Decimal) -> None:
    """Any non-negative Decimal must be accepted as a valid Money amount."""
    vo = Money(amount)
    assert vo.amount == amount
    assert vo.amount >= Decimal("0")


@given(amount=negative_decimals)
@settings(max_examples=50)
def test_money_rejects_negative(amount: Decimal) -> None:
    """Any negative Decimal must raise ValidationError."""
    with pytest.raises(ValidationError):
        Money(amount)


@given(amount=non_negative_decimals)
@settings(max_examples=50)
def test_money_equality_by_value(amount: Decimal) -> None:
    """Two Money instances with the same amount must be equal."""
    assert Money(amount) == Money(amount)


@given(a=non_negative_decimals, b=non_negative_decimals)
@settings(max_examples=50)
def test_money_inequality(a: Decimal, b: Decimal) -> None:
    """Two Money instances with different amounts must not be equal."""
    if a != b:
        assert Money(a) != Money(b)


@given(amount=non_negative_decimals)
@settings(max_examples=50)
def test_money_str_returns_amount(amount: Decimal) -> None:
    """str(Money) must equal str(amount)."""
    assert str(Money(amount)) == str(amount)


# ---------------------------------------------------------------------------
# Description
# ---------------------------------------------------------------------------


@given(text=any_text)
@settings(max_examples=100)
def test_description_accepts_any_string(text: str) -> None:
    """Description must accept any string without raising."""
    vo = Description(text)
    assert vo.value == text


def test_description_defaults_to_empty() -> None:
    """Description() with no arguments must default to empty string."""
    assert Description().value == ""


@given(text=any_text)
@settings(max_examples=50)
def test_description_equality_by_value(text: str) -> None:
    """Two Description instances with the same text must be equal."""
    assert Description(text) == Description(text)


@given(text=any_text)
@settings(max_examples=50)
def test_description_str_returns_value(text: str) -> None:
    """str(Description) must equal its stored value."""
    vo = Description(text)
    assert str(vo) == vo.value


# ---------------------------------------------------------------------------
# CategoryId
# ---------------------------------------------------------------------------


@given(uid=st.uuids())
@settings(max_examples=100)
def test_category_id_accepts_any_uuid(uid: uuid.UUID) -> None:
    """CategoryId must accept any valid UUID."""
    vo = CategoryId(uid)
    assert vo.value == uid


@given(uid=st.uuids())
@settings(max_examples=50)
def test_category_id_equality_by_value(uid: uuid.UUID) -> None:
    """Two CategoryId instances with the same UUID must be equal."""
    assert CategoryId(uid) == CategoryId(uid)


@given(a=st.uuids(), b=st.uuids())
@settings(max_examples=50)
def test_category_id_inequality(a: uuid.UUID, b: uuid.UUID) -> None:
    """Two CategoryId instances with different UUIDs must not be equal."""
    if a != b:
        assert CategoryId(a) != CategoryId(b)


@given(uid=st.uuids())
@settings(max_examples=50)
def test_category_id_str_returns_uuid_string(uid: uuid.UUID) -> None:
    """str(CategoryId) must return the string representation of the UUID."""
    assert str(CategoryId(uid)) == str(uid)
