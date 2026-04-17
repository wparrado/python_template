"""Value objects for the Item aggregate.

Each VO is immutable, self-validating, and compared by value.
They encapsulate domain rules that used to live inside Item._validate().
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.value_object import ValueObject


@dataclass(frozen=True)
class ItemName(ValueObject):
    """A non-empty, whitespace-stripped item name."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip() if self.value else ""
        if not stripped:
            raise ValidationError("Item name must not be empty")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Money(ValueObject):
    """A non-negative monetary amount."""

    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValidationError("Item price must be non-negative")

    def __str__(self) -> str:
        return str(self.amount)


@dataclass(frozen=True)
class Description(ValueObject):
    """An optional free-text description (defaults to empty string)."""

    value: str = ""

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CategoryId(ValueObject):
    """A reference to a Category by its UUID primary key.

    Typed wrapper that makes the foreign-key intent explicit in the domain
    model without introducing a hard dependency on the Category aggregate.
    """

    value: uuid.UUID

    def __str__(self) -> str:
        return str(self.value)
