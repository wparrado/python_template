"""Items CRUD router — example of a fully wired hexagonal endpoint.

Flow:
  HTTP request
    → JWT auth (CurrentUser dependency)
    → schema validation (Pydantic)
    → IItemApplicationService (application port)
    → domain aggregate (business logic + events)
    → repository adapter (infrastructure)
    → ItemOutputDTO
    → schema mapper (response)
    → HTTP response

Domain errors propagate as exceptions and are translated to HTTP
responses by the registered error handlers (see error_handlers.py).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable, Coroutine
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status

from app.application.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.application.dtos.auth_dtos import CurrentUser
from app.application.ports.item_application_service import IItemApplicationService
from app.presentation.api.v1.schemas.item_schemas import (
    CreateItemRequest,
    ItemResponse,
    PaginatedItemResponse,
    UpdateItemRequest,
)
from app.presentation.app_state import get_app_state
from app.presentation.mappers.item_schema_mapper import ItemSchemaMapper

router = APIRouter(prefix="/items", tags=["items"])


async def _get_item_service(request: Request) -> AsyncGenerator[IItemApplicationService, None]:
    async for item_service in get_app_state(request).item_service_dep():
        yield item_service


def _get_current_user_dep(request: Request) -> Callable[..., Coroutine[Any, Any, CurrentUser]]:
    return get_app_state(request).get_current_user


class _PaginationParams:
    """Reusable FastAPI dependency for limit/offset pagination query params."""

    def __init__(
        self,
        limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Max items to return"),
        offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    ) -> None:
        self.limit = limit
        self.offset = offset


class _ItemSearchParams:
    """FastAPI dependency that groups item search filter query parameters."""

    def __init__(
        self,
        min_price: Annotated[Decimal | None, Query(ge=0.0, description="Minimum price (inclusive)")] = None,
        max_price: Annotated[Decimal | None, Query(ge=0.0, description="Maximum price (inclusive)")] = None,
        name_contains: Annotated[str | None, Query(min_length=1, max_length=255, description="Name keyword")] = None,
    ) -> None:
        self.min_price = min_price
        self.max_price = max_price
        self.name_contains = name_contains


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: CreateItemRequest,
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> ItemResponse:
    """Create a new item. Requires authentication."""
    dto = await service.create_item(
        name=body.name, price=body.price, description=body.description, category_id=body.category_id
    )
    return ItemSchemaMapper.to_response(dto)


@router.get("", response_model=PaginatedItemResponse)
async def list_items(
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
    pagination: Annotated[_PaginationParams, Depends()],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> PaginatedItemResponse:
    """List items with pagination metadata (total, has_next, has_previous). Requires authentication."""
    paginated = await service.list_items(limit=pagination.limit, offset=pagination.offset)
    return ItemSchemaMapper.to_paginated_response(paginated)


@router.get("/search", response_model=PaginatedItemResponse)
async def search_items(
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
    filters: Annotated[_ItemSearchParams, Depends()],
    pagination: Annotated[_PaginationParams, Depends()],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> PaginatedItemResponse:
    """Search items by optional price range and/or name keyword, with pagination metadata. Requires authentication."""
    paginated = await service.search_items(ItemSchemaMapper.to_search_params(filters, pagination))
    return ItemSchemaMapper.to_paginated_response(paginated)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: uuid.UUID,
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> ItemResponse:
    """Get a single item by ID. Requires authentication."""
    dto = await service.get_item(item_id)
    return ItemSchemaMapper.to_response(dto)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: uuid.UUID,
    body: UpdateItemRequest,
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> ItemResponse:
    """Update an existing item. Requires authentication."""
    dto = await service.update_item(
        item_id=item_id,
        name=body.name,
        price=body.price,
        description=body.description,
        category_id=body.category_id,
    )
    return ItemSchemaMapper.to_response(dto)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
    _current_user: Annotated[CurrentUser, Depends(_get_current_user_dep)],
) -> None:
    """Delete an item by ID.  Idempotent: returns 204 even if the item does not exist.

    Requires authentication.
    """
    await service.delete_item(item_id)
