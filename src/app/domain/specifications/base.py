"""Specification pattern — composable domain predicates.

A Specification encapsulates a single business rule as a first-class
object.  Specifications are combined with ``&`` (AND), ``|`` (OR), and
``~`` (NOT) to form composite rules without if/else chains in the domain.

Usage::

    active = ActiveItemSpecification()
    cheap  = PriceInRangeSpecification(max_price=Decimal("10"))
    query  = active & cheap
    items  = [i for i in all_items if query.is_satisfied_by(i)]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """Abstract base for all domain specifications.

    Subclass and implement ``is_satisfied_by`` to express a business rule.
    Use ``&``, ``|``, and ``~`` to compose specifications without
    inheriting from this class again.
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Return True if *candidate* satisfies this specification."""

    def __and__(self, other: Specification[T]) -> Specification[T]:
        """Return a specification satisfied when *both* operands are satisfied."""
        return _AndSpecification(self, other)

    def __or__(self, other: Specification[T]) -> Specification[T]:
        """Return a specification satisfied when *either* operand is satisfied."""
        return _OrSpecification(self, other)

    def __invert__(self) -> Specification[T]:
        """Return the logical negation of this specification."""
        return _NotSpecification(self)


class _AndSpecification(Specification[T]):
    """Composite: satisfied when both inner specifications are satisfied."""

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(candidate)


class _OrSpecification(Specification[T]):
    """Composite: satisfied when at least one inner specification is satisfied."""

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(candidate)


class _NotSpecification(Specification[T]):
    """Composite: satisfied when the inner specification is *not* satisfied."""

    def __init__(self, spec: Specification[T]) -> None:
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._spec.is_satisfied_by(candidate)
