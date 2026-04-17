"""Category command objects (CQRS — write side).

Commands express intent to change state.
They carry all the data needed to execute the operation.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateCategoryCommand:
    """Command to create a new category."""

    name: str
    description: str = ""
    slug: str | None = None
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class UpdateCategoryCommand:
    """Command to update an existing category (all fields optional)."""

    category_id: uuid.UUID
    name: str | None = None
    description: str | None = None
    slug: str | None = None
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class DeleteCategoryCommand:
    """Command to delete a category by ID."""

    category_id: uuid.UUID
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)
