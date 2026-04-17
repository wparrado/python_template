"""Value objects for the Category aggregate.

Each VO is immutable, self-validating, and compared by value.
They encapsulate domain rules such as slug format and name length constraints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.exceptions.domain_errors import ValidationError
from app.domain.model.value_object import ValueObject

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class CategoryName(ValueObject):
    """A non-empty, whitespace-stripped category name (max 100 chars)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip() if self.value else ""
        if not stripped:
            raise ValidationError("Category name must not be empty")
        if len(stripped) > 100:
            raise ValidationError("Category name must not exceed 100 characters")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value

    def to_slug(self) -> str:
        """Derive a URL-safe slug from this name (lowercase, hyphens for spaces)."""
        slug = self.value.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-{2,}", "-", slug).strip("-")
        return slug or "category"


@dataclass(frozen=True)
class CategorySlug(ValueObject):
    """A URL-safe slug: lowercase, alphanumeric characters and hyphens only."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValidationError("Category slug must not be empty")
        if not _SLUG_RE.match(self.value):
            raise ValidationError("Category slug must be lowercase alphanumeric with hyphens (e.g. 'my-category')")
        if len(self.value) > 100:
            raise ValidationError("Category slug must not exceed 100 characters")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CategoryDescription(ValueObject):
    """An optional free-text description for a category (max 500 chars)."""

    value: str = ""

    def __post_init__(self) -> None:
        if len(self.value) > 500:
            raise ValidationError("Category description must not exceed 500 characters")

    def __str__(self) -> str:
        return self.value
