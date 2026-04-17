"""Item DTOs — Pydantic models at the application layer boundary.

These are the I/O models for command/query handlers.
They are the ONLY place Pydantic is allowed in the application layer.
Domain entities must never be returned directly to outer layers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ItemInputDTO(BaseModel):
    """Input for creating an item."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=255)
    price: Decimal = Field(..., ge=Decimal("0"))
    description: str = Field(default="", max_length=1000)


class ItemUpdateDTO(BaseModel):
    """Input for updating an item (all fields optional)."""

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=Decimal("0"))
    description: str | None = Field(default=None, max_length=1000)


class ItemSearchParams(BaseModel):
    """Input parameters for searching items.

    All filter and pagination fields are optional.
    Omit a filter to leave that dimension unconstrained.
    """

    model_config = ConfigDict(frozen=True)

    min_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    max_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    name_contains: str | None = Field(default=None, min_length=1, max_length=255)
    limit: int = Field(default=50, ge=1)
    offset: int = Field(default=0, ge=0)


class ItemOutputDTO(BaseModel):
    """Output representing an item returned from a use case."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    price: Decimal
    description: str
    category_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
