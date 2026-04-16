"""Result[T, E] — typed return value for use-case handlers.

Errors do not cross layer boundaries as bare exceptions.
Each layer maps errors to its own types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


@dataclass(frozen=True)
class Success[T]:
    """Represents a successful result holding a value of type T."""

    value: T

    @property
    def is_success(self) -> bool:
        """Return True since this is a successful result."""
        return True

    @property
    def is_failure(self) -> bool:
        """Return False since this is not a failure."""
        return False


@dataclass(frozen=True)
class Failure[E]:
    """Represents a failed result holding an error of type E."""

    error: E

    @property
    def is_success(self) -> bool:
        """Return False since this is not a successful result."""
        return False

    @property
    def is_failure(self) -> bool:
        """Return True since this is a failure."""
        return True


type Result[T, E] = Success[T] | Failure[E]
