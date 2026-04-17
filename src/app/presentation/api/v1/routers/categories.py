"""Categories CRUD router — second bounded context in the hexagonal architecture.

Flow:
  HTTP request
    → JWT auth (CurrentUser dependency)
    → schema validation (Pydantic)
    → ICategoryApplicationService (application port)
    → domain aggregate (business logic + events)
    → repository adapter (infrastructure)
    → CategoryOutputDTO
    → schema mapper (response)
    → HTTP response

Domain errors propagate as exceptions and are translated to HTTP
responses by the registered error handlers (see error_handlers.py).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status

from app.application.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.application.dtos.auth_dtos import CurrentUser
from app.application.ports.category_application_service import ICategoryApplicationService
from app.presentation.api.v1.schemas.category_schemas import (
    CategoryResponse,
    CreateCategoryRequest,
    PaginatedCategoryResponse,
    UpdateCategoryRequest,
)
from app.presentation.app_state import get_app_state
from app.presentation.mappers.category_schema_mapper import CategorySchemaMapper

router = APIRouter(prefix="/categories", tags=["categories"])


async def _get_category_service(request: Request) -> AsyncGenerator[ICategoryApplicationService, None]:
    async for category_service in get_app_state(request).category_service_dep():
        yield category_service


def _get_current_user_dep(request: Request) -> Callable[..., Coroutine[Any, Any, CurrentUser]]:
    return get_app_state(request).get_current_user


class _PaginationParams:
    """Reusable FastAPI dependency for limit/offset pagination query params."""

    def __init__(
        self,
        limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Max categories to return"),
        offset: int = Query(default=0, ge=0, description="Number of categories to skip"),
    ) -> None:
        self.limit = limit
        self.offset = offset


class _CategorySearchParams:
    """FastAPI dependency that groups category search filter query parameters."""

    def __init__(
        self,
        name_contains: str | None = Query(default=None, min_length=1, max_length=100, description="Name keyword"),
        slug: str | None = Query(default=None, min_length=1, max_length=100, description="Exact slug match"),
    ) -> None:
        self.name_contains = name_contains
        self.slug = slug


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CreateCategoryRequest,
    service: Annotated[ICategoryApplicationService, Depends(_get_category_service)],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> CategoryResponse:
    """Create a new category. Requires authentication."""
    dto = await service.create_category(name=body.name, description=body.description, slug=body.slug)
    return CategorySchemaMapper.to_response(dto)


@router.get("", response_model=PaginatedCategoryResponse)
async def list_categories(
    service: Annotated[ICategoryApplicationService, Depends(_get_category_service)],
    pagination: Annotated[_PaginationParams, Depends()],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> PaginatedCategoryResponse:
    """List categories with pagination metadata (total, has_next, has_previous). Requires authentication."""
    paginated = await service.list_categories(limit=pagination.limit, offset=pagination.offset)
    return CategorySchemaMapper.to_paginated_response(paginated)


@router.get("/search", response_model=PaginatedCategoryResponse)
async def search_categories(
    service: Annotated[ICategoryApplicationService, Depends(_get_category_service)],
    filters: Annotated[_CategorySearchParams, Depends()],
    pagination: Annotated[_PaginationParams, Depends()],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> PaginatedCategoryResponse:
    """Search categories by optional name keyword and/or slug, with pagination metadata. Requires authentication."""
    paginated = await service.search_categories(CategorySchemaMapper.to_search_params(filters, pagination))
    return CategorySchemaMapper.to_paginated_response(paginated)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    service: Annotated[ICategoryApplicationService, Depends(_get_category_service)],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> CategoryResponse:
    """Get a single category by ID. Requires authentication."""
    dto = await service.get_category(category_id)
    return CategorySchemaMapper.to_response(dto)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    body: UpdateCategoryRequest,
    service: Annotated[ICategoryApplicationService, Depends(_get_category_service)],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> CategoryResponse:
    """Update an existing category. Requires authentication."""
    dto = await service.update_category(
        category_id=category_id,
        name=body.name,
        description=body.description,
        slug=body.slug,
    )
    return CategorySchemaMapper.to_response(dto)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    service: Annotated[ICategoryApplicationService, Depends(_get_category_service)],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> None:
    """Delete a category by ID.  Idempotent: returns 204 even if the category does not exist.

    Requires authentication.
    """
    await service.delete_category(category_id)
