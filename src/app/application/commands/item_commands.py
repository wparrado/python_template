"""Item command objects (CQRS — write side).

Commands express intent to change state.
They carry all the data needed to execute the operation.
No external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateItemCommand:
    name: str
    price: float
    description: str = ""
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class UpdateItemCommand:
    item_id: uuid.UUID
    name: str | None = None
    price: float | None = None
    description: str | None = None
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class DeleteItemCommand:
    item_id: uuid.UUID
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)
