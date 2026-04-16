"""Items CRUD router — example of a fully wired hexagonal endpoint.

Flow:
  HTTP request
    → schema validation (Pydantic)
    → schema mapper (presentation DTO)
    → command/query handler (application layer)
    → domain aggregate (business logic + events)
    → repository adapter (infrastructure)
    → Result[DTO, DomainError]
    → schema mapper (response)
    → HTTP response
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.application.commands.item_commands import (
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from app.application.exceptions import DomainError, NotFoundError, ValidationError
from app.application.handlers.command_handlers import (
    CreateItemHandler,
    DeleteItemHandler,
    UpdateItemHandler,
)
from app.application.handlers.query_handlers import GetItemHandler, ListItemsHandler
from app.application.queries.item_queries import GetItemQuery, ListItemsQuery
from app.application.result import Failure
from app.presentation.api.v1.schemas.item_schemas import (
    CreateItemRequest,
    ItemResponse,
    UpdateItemRequest,
)
from app.presentation.mappers.item_schema_mapper import ItemSchemaMapper

router = APIRouter(prefix="/items", tags=["items"])


def _get_create_handler(request: Request) -> CreateItemHandler:
    return request.app.state.container.create_item_handler()  # type: ignore[no-any-return]


def _get_update_handler(request: Request) -> UpdateItemHandler:
    return request.app.state.container.update_item_handler()  # type: ignore[no-any-return]


def _get_delete_handler(request: Request) -> DeleteItemHandler:
    return request.app.state.container.delete_item_handler()  # type: ignore[no-any-return]


def _get_get_handler(request: Request) -> GetItemHandler:
    return request.app.state.container.get_item_handler()  # type: ignore[no-any-return]


def _get_list_handler(request: Request) -> ListItemsHandler:
    return request.app.state.container.list_items_handler()  # type: ignore[no-any-return]


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: CreateItemRequest,
    handler: Annotated[CreateItemHandler, Depends(_get_create_handler)],
) -> ItemResponse:
    """Create a new item."""
    command = CreateItemCommand(name=body.name, price=body.price, description=body.description)
    result = await handler.handle(command)
    if isinstance(result, Failure):
        raise HTTPException(status_code=400, detail=result.error.message)
    return ItemSchemaMapper.to_response(result.value)


@router.get("", response_model=list[ItemResponse])
async def list_items(
    handler: Annotated[ListItemsHandler, Depends(_get_list_handler)],
) -> list[ItemResponse]:
    """List all items."""
    result = await handler.handle(ListItemsQuery())
    if isinstance(result, Failure):
        raise HTTPException(status_code=500, detail=result.error.message)
    return ItemSchemaMapper.to_response_list(result.value)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: uuid.UUID,
    handler: Annotated[GetItemHandler, Depends(_get_get_handler)],
) -> ItemResponse:
    """Get a single item by ID."""
    result = await handler.handle(GetItemQuery(item_id=item_id))
    if isinstance(result, Failure):
        raise _domain_error_to_http(result.error)
    return ItemSchemaMapper.to_response(result.value)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: uuid.UUID,
    body: UpdateItemRequest,
    handler: Annotated[UpdateItemHandler, Depends(_get_update_handler)],
) -> ItemResponse:
    """Update an existing item."""
    command = UpdateItemCommand(
        item_id=item_id,
        name=body.name,
        price=body.price,
        description=body.description,
    )
    result = await handler.handle(command)
    if isinstance(result, Failure):
        raise _domain_error_to_http(result.error)
    return ItemSchemaMapper.to_response(result.value)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    handler: Annotated[DeleteItemHandler, Depends(_get_delete_handler)],
) -> None:
    """Delete an item by ID."""
    command = DeleteItemCommand(item_id=item_id)
    result = await handler.handle(command)
    if isinstance(result, Failure):
        raise _domain_error_to_http(result.error)


def _domain_error_to_http(error: DomainError) -> HTTPException:
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=404, detail=error.message)
    if isinstance(error, ValidationError):
        return HTTPException(status_code=422, detail=error.message)
    return HTTPException(status_code=400, detail=error.message)
