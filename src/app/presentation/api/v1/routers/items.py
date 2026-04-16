"""Items CRUD router — example of a fully wired hexagonal endpoint.

Flow:
  HTTP request
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
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.application.ports.item_application_service import IItemApplicationService
from app.presentation.app_state import get_app_state
from app.presentation.api.v1.schemas.item_schemas import (
    CreateItemRequest,
    ItemResponse,
    UpdateItemRequest,
)
from app.presentation.mappers.item_schema_mapper import ItemSchemaMapper

router = APIRouter(prefix="/items", tags=["items"])

_MAX_PAGE_SIZE = 1000
_DEFAULT_PAGE_SIZE = 50


def _get_item_service(request: Request) -> IItemApplicationService:
    return get_app_state(request).item_service


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: CreateItemRequest,
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
) -> ItemResponse:
    """Create a new item."""
    dto = await service.create_item(name=body.name, price=body.price, description=body.description)
    return ItemSchemaMapper.to_response(dto)


@router.get("", response_model=list[ItemResponse])
async def list_items(
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
) -> list[ItemResponse]:
    """List items with optional pagination."""
    dtos = await service.list_items(limit=limit, offset=offset)
    return ItemSchemaMapper.to_response_list(dtos)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: uuid.UUID,
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
) -> ItemResponse:
    """Get a single item by ID."""
    dto = await service.get_item(item_id)
    return ItemSchemaMapper.to_response(dto)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: uuid.UUID,
    body: UpdateItemRequest,
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
) -> ItemResponse:
    """Update an existing item."""
    dto = await service.update_item(
        item_id=item_id,
        name=body.name,
        price=body.price,
        description=body.description,
    )
    return ItemSchemaMapper.to_response(dto)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    service: Annotated[IItemApplicationService, Depends(_get_item_service)],
) -> None:
    """Delete an item by ID.  Idempotent: returns 204 even if the item does not exist."""
    await service.delete_item(item_id)
