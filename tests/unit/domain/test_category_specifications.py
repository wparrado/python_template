"""Unit tests for domain Category specifications."""

from __future__ import annotations

import pytest

from app.domain.model.example.category import Category
from app.domain.specifications.category_specifications import (
    ActiveCategorySpecification,
    AllCategoriesSpecification,
    NameContainsCategorySpecification,
    SlugMatchesSpecification,
)


@pytest.fixture
def active_category() -> Category:
    return Category.create(name="Electronics", description="Electronic devices")


@pytest.fixture
def deleted_category() -> Category:
    cat = Category.create(name="Old Category", description="Deprecated")
    cat.mark_deleted()
    return cat


@pytest.fixture
def slug_category() -> Category:
    return Category.create(name="Home Appliances", slug="home-appliances")


# ---------------------------------------------------------------------------
# AllCategoriesSpecification
# ---------------------------------------------------------------------------


def test_all_categories_matches_active(active_category: Category) -> None:
    assert AllCategoriesSpecification().is_satisfied_by(active_category)


def test_all_categories_matches_deleted(deleted_category: Category) -> None:
    assert AllCategoriesSpecification().is_satisfied_by(deleted_category)


# ---------------------------------------------------------------------------
# ActiveCategorySpecification
# ---------------------------------------------------------------------------


def test_active_spec_matches_active_category(active_category: Category) -> None:
    assert ActiveCategorySpecification().is_satisfied_by(active_category)


def test_active_spec_rejects_deleted_category(deleted_category: Category) -> None:
    assert not ActiveCategorySpecification().is_satisfied_by(deleted_category)


# ---------------------------------------------------------------------------
# SlugMatchesSpecification
# ---------------------------------------------------------------------------


def test_slug_matches_exact(slug_category: Category) -> None:
    assert SlugMatchesSpecification("home-appliances").is_satisfied_by(slug_category)


def test_slug_no_match_different_slug(slug_category: Category) -> None:
    assert not SlugMatchesSpecification("electronics").is_satisfied_by(slug_category)


def test_slug_case_sensitive(slug_category: Category) -> None:
    assert not SlugMatchesSpecification("Home-Appliances").is_satisfied_by(slug_category)


def test_slug_property_returns_slug() -> None:
    spec = SlugMatchesSpecification("my-slug")
    assert spec.slug == "my-slug"


# ---------------------------------------------------------------------------
# NameContainsCategorySpecification
# ---------------------------------------------------------------------------


def test_name_contains_case_insensitive(active_category: Category) -> None:
    assert NameContainsCategorySpecification("ELEC").is_satisfied_by(active_category)
    assert NameContainsCategorySpecification("elec").is_satisfied_by(active_category)
    assert NameContainsCategorySpecification("Electronics").is_satisfied_by(active_category)


def test_name_contains_partial_match(active_category: Category) -> None:
    assert NameContainsCategorySpecification("lect").is_satisfied_by(active_category)


def test_name_contains_no_match(active_category: Category) -> None:
    assert not NameContainsCategorySpecification("furniture").is_satisfied_by(active_category)


def test_name_contains_keyword_is_lowercased() -> None:
    spec = NameContainsCategorySpecification("UPPER")
    assert spec.keyword == "upper"


# ---------------------------------------------------------------------------
# Composite specifications (And / Or / Not via operators)
# ---------------------------------------------------------------------------


def test_and_spec_both_satisfied(active_category: Category) -> None:
    spec = ActiveCategorySpecification() & NameContainsCategorySpecification("elec")
    assert spec.is_satisfied_by(active_category)


def test_and_spec_one_fails(deleted_category: Category) -> None:
    spec = ActiveCategorySpecification() & NameContainsCategorySpecification("old")
    assert not spec.is_satisfied_by(deleted_category)


def test_or_spec_one_satisfied(deleted_category: Category) -> None:
    spec = ActiveCategorySpecification() | NameContainsCategorySpecification("old")
    assert spec.is_satisfied_by(deleted_category)


def test_or_spec_none_satisfied(active_category: Category) -> None:
    spec = NameContainsCategorySpecification("xyz") | SlugMatchesSpecification("nope")
    assert not spec.is_satisfied_by(active_category)


def test_not_spec_inverts_active(active_category: Category) -> None:
    assert not (~ActiveCategorySpecification()).is_satisfied_by(active_category)


def test_not_spec_inverts_deleted(deleted_category: Category) -> None:
    assert (~ActiveCategorySpecification()).is_satisfied_by(deleted_category)


def test_complex_composition(active_category: Category) -> None:
    spec = ActiveCategorySpecification() & NameContainsCategorySpecification("elec") & ~SlugMatchesSpecification("nope")
    assert spec.is_satisfied_by(active_category)
