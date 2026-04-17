"""Category DTOs — Pydantic models at the application layer boundary.

These are the I/O models for command/query handlers.
They are the ONLY place Pydantic is allowed in the application layer.
Domain entities must never be returned directly to outer layers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryInputDTO(BaseModel):
    """Input for creating a category."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CategoryUpdateDTO(BaseModel):
    """Input for updating a category (all fields optional)."""

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CategorySearchParams(BaseModel):
    """Input parameters for searching categories.

    All filter and pagination fields are optional.
    Omit a filter to leave that dimension unconstrained.
    """

    model_config = ConfigDict(frozen=True)

    name_contains: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=50, ge=1)
    offset: int = Field(default=0, ge=0)


class CategoryOutputDTO(BaseModel):
    """Output representing a category returned from a use case."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str
    created_at: datetime
    updated_at: datetime
