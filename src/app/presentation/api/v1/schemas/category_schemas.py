"""Pydantic request/response schemas for the categories API.

These live in the presentation layer and are NOT DTOs.
A mapper converts between these and application DTOs.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateCategoryRequest(BaseModel):
    """Request body for creating a category."""

    name: str = Field(..., min_length=1, max_length=100, examples=["Electronics"])
    description: str = Field(default="", max_length=500, examples=["Electronic devices and accessories"])
    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        examples=["electronics"],
    )


class UpdateCategoryRequest(BaseModel):
    """Request body for updating a category (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


class CategoryResponse(BaseModel):
    """API response schema for a single category."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str
    created_at: datetime
    updated_at: datetime


class PaginatedCategoryResponse(BaseModel):
    """API response schema for a paginated list of categories.

    Includes navigation metadata so clients can determine whether
    additional pages exist without issuing a separate count query.
    """

    model_config = ConfigDict(frozen=True)

    items: list[CategoryResponse]
    total: int = Field(..., description="Total number of categories matching the query")
    limit: int = Field(..., description="Maximum categories per page (as requested)")
    offset: int = Field(..., description="Number of categories skipped before this page")
    has_next: bool = Field(..., description="True when more categories exist beyond this page")
    has_previous: bool = Field(..., description="True when this is not the first page")
