"""Concrete domain specifications for the Category aggregate.

Each class encodes one business rule that can be used standalone or
composed with ``&``, ``|``, ``~`` operators from the base Specification.
"""

from __future__ import annotations

from app.domain.model.example.category import Category
from app.domain.specifications.base import Specification


class AllCategoriesSpecification(Specification[Category]):
    """Matches every category — neutral element for specification composition."""

    def is_satisfied_by(self, candidate: Category) -> bool:
        return True


class ActiveCategorySpecification(Specification[Category]):
    """Matches categories that have not been soft-deleted."""

    def is_satisfied_by(self, candidate: Category) -> bool:
        return not candidate.is_deleted


class SlugMatchesSpecification(Specification[Category]):
    """Matches the category whose slug equals *slug* (exact, case-sensitive)."""

    def __init__(self, slug: str) -> None:
        self._slug = slug

    @property
    def slug(self) -> str:
        """The slug to match against."""
        return self._slug

    def is_satisfied_by(self, candidate: Category) -> bool:
        return candidate.slug.value == self._slug


class NameContainsCategorySpecification(Specification[Category]):
    """Matches categories whose name contains *keyword* (case-insensitive)."""

    def __init__(self, keyword: str) -> None:
        self._keyword = keyword.lower()

    @property
    def keyword(self) -> str:
        """Normalised (lowercased) keyword to search for within category names."""
        return self._keyword

    def is_satisfied_by(self, candidate: Category) -> bool:
        return self._keyword in candidate.name.value.lower()
