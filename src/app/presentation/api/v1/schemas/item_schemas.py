"""Pydantic request/response schemas for the items API.

These live in the presentation layer and are NOT DTOs.
A mapper converts between these and application DTOs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CreateItemRequest(BaseModel):
    """Request body for creating an item."""

    name: str = Field(..., min_length=1, max_length=255, examples=["Widget"])
    price: Decimal = Field(..., ge=Decimal("0"), decimal_places=10, examples=["9.99"])
    description: str = Field(default="", max_length=1000, examples=["A useful widget"])


class UpdateItemRequest(BaseModel):
    """Request body for updating an item (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=10)
    description: str | None = Field(default=None, max_length=1000)


class ItemResponse(BaseModel):
    """API response schema for an item.

    ``price`` is serialised as a JSON float for broad client compatibility.
    Monetary computations should always use the Decimal-typed application DTOs.
    """

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    price: float
    description: str
    created_at: datetime
    updated_at: datetime
