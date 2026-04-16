"""DomainError -> HTTPException mapper.

Registered at application startup so FastAPI returns the correct
HTTP status codes for domain errors.
No domain logic here — only translation.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.exceptions import (
    ConflictError,
    DomainError,
    ItemNotFoundError,
    NotFoundError,
    ValidationError,
)


def register_error_handlers(app: FastAPI) -> None:
    """Register domain exception handlers that map errors to HTTP responses."""

    @app.exception_handler(ItemNotFoundError)
    async def item_not_found_handler(_request: Request, exc: ItemNotFoundError) -> JSONResponse:
        """Map ItemNotFoundError to HTTP 404."""
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        """Map NotFoundError to HTTP 404."""
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(ValidationError)
    async def validation_error_handler(_request: Request, exc: ValidationError) -> JSONResponse:
        """Map ValidationError to HTTP 422."""
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(ConflictError)
    async def conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
        """Map ConflictError to HTTP 409."""
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        """Map any unhandled DomainError to HTTP 400."""
        return JSONResponse(status_code=400, content={"detail": exc.message})
