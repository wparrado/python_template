"""Item DTOs — Pydantic models at the application layer boundary.

These are the I/O models for command/query handlers.
They are the ONLY place Pydantic is allowed in the application layer.
Domain entities must never be returned directly to outer layers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemInputDTO(BaseModel):
    """Input for creating an item."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., ge=0)
    description: str = Field(default="", max_length=1000)


class ItemUpdateDTO(BaseModel):
    """Input for updating an item (all fields optional)."""

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=1000)


class ItemOutputDTO(BaseModel):
    """Output representing an item returned from a use case."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    price: float
    description: str
    created_at: datetime
    updated_at: datetime
