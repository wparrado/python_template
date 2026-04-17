"""Concrete domain specifications for the Item aggregate.

Each class encodes one business rule that can be used standalone or
composed with ``&``, ``|``, ``~`` operators from the base Specification.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.model.example.item import Item
from app.domain.specifications.base import Specification


class AllItemsSpecification(Specification[Item]):
    """Matches every item — neutral element for specification composition."""

    def is_satisfied_by(self, candidate: Item) -> bool:
        return True


class ActiveItemSpecification(Specification[Item]):
    """Matches items that have not been soft-deleted."""

    def is_satisfied_by(self, candidate: Item) -> bool:
        return not candidate.is_deleted


class PriceInRangeSpecification(Specification[Item]):
    """Matches items whose price falls within [min_price, max_price].

    Either bound is optional: pass ``None`` to leave that end open.
    """

    def __init__(
        self,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> None:
        self._min = min_price
        self._max = max_price

    @property
    def min_price(self) -> Decimal | None:
        """Lower bound of the price range, inclusive. ``None`` means unbounded."""
        return self._min

    @property
    def max_price(self) -> Decimal | None:
        """Upper bound of the price range, inclusive. ``None`` means unbounded."""
        return self._max

    def is_satisfied_by(self, candidate: Item) -> bool:
        if self._min is not None and candidate.price.amount < self._min:
            return False
        if self._max is not None and candidate.price.amount > self._max:
            return False
        return True


class NameContainsSpecification(Specification[Item]):
    """Matches items whose name contains *keyword* (case-insensitive)."""

    def __init__(self, keyword: str) -> None:
        self._keyword = keyword.lower()

    @property
    def keyword(self) -> str:
        """Normalised (lowercased) keyword to search for within item names."""
        return self._keyword

    def is_satisfied_by(self, candidate: Item) -> bool:
        return self._keyword in candidate.name.value.lower()
