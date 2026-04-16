"""ValueObject base.

Value objects are immutable and compared by value, not identity.
They encapsulate validation of primitive types.
No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Base class for all value objects.

    Subclasses should be frozen dataclasses.
    Use __post_init__ for invariant validation.
    """

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
