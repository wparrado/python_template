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
    @app.exception_handler(ItemNotFoundError)
    async def item_not_found_handler(request: Request, exc: ItemNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(ConflictError)
    async def conflict_handler(  # pylint: disable=unused-argument
        request: Request, exc: ConflictError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(DomainError)
    async def domain_error_handler(  # pylint: disable=unused-argument
        request: Request, exc: DomainError
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.message})
