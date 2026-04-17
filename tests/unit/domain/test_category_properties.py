"""Property-based tests for the Category domain model.

Uses Hypothesis to generate arbitrary valid/invalid inputs and verify
that domain invariants hold for all inputs, not just hand-picked examples.

Strategies
----------
- ``valid_category_names``: non-empty stripped strings (≤100 chars)
- ``valid_slugs``: lowercase alphanumeric + hyphens, per _SLUG_RE
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.example.category import Category
from app.domain.specifications.category_specifications import (
    ActiveCategorySpecification,
    AllCategoriesSpecification,
    NameContainsCategorySpecification,
    SlugMatchesSpecification,
)

# ---------------------------------------------------------------------------
# Custom strategies
# ---------------------------------------------------------------------------

valid_category_names = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != "")

# Slugs must match ^[a-z0-9]+(?:-[a-z0-9]+)*$
valid_slugs = st.from_regex(r"[a-z0-9]+(-[a-z0-9]+)*", fullmatch=True).filter(lambda s: len(s) <= 100)

invalid_category_names = st.one_of(
    st.just(""),
    st.just("   "),
    st.text(min_size=101, max_size=120).filter(lambda s: s.strip() != ""),
)


# ---------------------------------------------------------------------------
# Category.create invariants
# ---------------------------------------------------------------------------


@given(name=valid_category_names)
@settings(max_examples=100)
def test_valid_name_always_creates(name: str) -> None:
    """Any valid name must produce a Category with a stripped name."""
    category = Category.create(name=name)
    assert category.name.value == name.strip()
    assert not category.is_deleted


@given(name=valid_category_names)
@settings(max_examples=50)
def test_create_derives_non_empty_slug(name: str) -> None:
    """Auto-derived slug must always be non-empty."""
    category = Category.create(name=name)
    assert len(category.slug.value) > 0


@given(name=valid_category_names)
@settings(max_examples=50)
def test_collect_events_clears_after_first_call(name: str) -> None:
    """collect_events() must drain the queue; second call returns []."""
    category = Category.create(name=name)
    category.collect_events()
    assert category.collect_events() == []


def test_empty_name_raises() -> None:
    with pytest.raises(ValidationError):
        Category.create(name="")


def test_whitespace_only_name_raises() -> None:
    with pytest.raises(ValidationError):
        Category.create(name="   ")


def test_name_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        Category.create(name="a" * 101)


# ---------------------------------------------------------------------------
# AllCategoriesSpecification — always True
# ---------------------------------------------------------------------------


@given(name=valid_category_names)
@settings(max_examples=50)
def test_all_categories_spec_always_true(name: str) -> None:
    category = Category.create(name=name)
    assert AllCategoriesSpecification().is_satisfied_by(category)


# ---------------------------------------------------------------------------
# ActiveCategorySpecification
# ---------------------------------------------------------------------------


@given(name=valid_category_names)
@settings(max_examples=50)
def test_active_spec_true_before_deletion(name: str) -> None:
    category = Category.create(name=name)
    assert ActiveCategorySpecification().is_satisfied_by(category)


@given(name=valid_category_names)
@settings(max_examples=50)
def test_active_spec_false_after_deletion(name: str) -> None:
    category = Category.create(name=name)
    category.mark_deleted()
    assert not ActiveCategorySpecification().is_satisfied_by(category)


# ---------------------------------------------------------------------------
# SlugMatchesSpecification
# ---------------------------------------------------------------------------


@given(slug=valid_slugs)
@settings(max_examples=50)
def test_slug_matches_own_slug(slug: str) -> None:
    """A category created with an explicit slug must match that slug."""
    category = Category.create(name="Test Category", slug=slug)
    assert SlugMatchesSpecification(slug).is_satisfied_by(category)


@given(slug=valid_slugs)
@settings(max_examples=50)
def test_different_slug_does_not_match(slug: str) -> None:
    """A different slug must not match."""
    category = Category.create(name="Test Category", slug=slug)
    other_slug = slug + "x"
    # 'other_slug' may exceed max length or be invalid — just verify it doesn't match
    assert not SlugMatchesSpecification(other_slug).is_satisfied_by(category)


# ---------------------------------------------------------------------------
# NameContainsCategorySpecification
# ---------------------------------------------------------------------------


@given(name=valid_category_names)
@settings(max_examples=50)
def test_name_contains_full_name_always_matches(name: str) -> None:
    """Searching by the stored (stripped, lower) name always finds the category."""
    category = Category.create(name=name)
    stored = category.name.value.lower()
    assert NameContainsCategorySpecification(stored).is_satisfied_by(category)


@given(name=valid_category_names)
@settings(max_examples=50)
def test_empty_keyword_always_matches(name: str) -> None:
    """An empty keyword matches every category name."""
    category = Category.create(name=name)
    assert NameContainsCategorySpecification("").is_satisfied_by(category)


# ---------------------------------------------------------------------------
# Composition: And / Or / Not laws
# ---------------------------------------------------------------------------


@given(name=valid_category_names)
@settings(max_examples=50)
def test_not_not_is_identity(name: str) -> None:
    """¬¬P ≡ P for ActiveCategorySpecification."""
    category = Category.create(name=name)
    spec = ActiveCategorySpecification()
    assert (~(~spec)).is_satisfied_by(category) == spec.is_satisfied_by(category)


@given(name=valid_category_names)
@settings(max_examples=50)
def test_and_commutative(name: str) -> None:
    """A & B ≡ B & A."""
    category = Category.create(name=name)
    a = ActiveCategorySpecification()
    b = AllCategoriesSpecification()
    assert (a & b).is_satisfied_by(category) == (b & a).is_satisfied_by(category)


@given(name=valid_category_names)
@settings(max_examples=50)
def test_or_commutative(name: str) -> None:
    """A | B ≡ B | A."""
    category = Category.create(name=name)
    a = ActiveCategorySpecification()
    b = AllCategoriesSpecification()
    assert (a | b).is_satisfied_by(category) == (b | a).is_satisfied_by(category)
