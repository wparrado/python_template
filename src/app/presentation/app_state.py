"""Typed application state container.

FastAPI's ``app.state`` is an untyped namespace by default.  This module
provides a strongly-typed wrapper so that router code can access state
members without ``# type: ignore`` suppressions.

Usage (in a router):
    from app.presentation.app_state import get_app_state

    def _get_item_service_dep(request: Request):
        return get_app_state(request).item_service_dep
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from app.application.dtos.auth_dtos import CurrentUser
from app.application.ports.category_application_service import ICategoryApplicationService
from app.application.ports.item_application_service import IItemApplicationService
from app.application.ports.health_check import IHealthCheck


@dataclass
class AppState:
    """Typed snapshot of presentation-relevant ``app.state`` fields.

    Only holds references to application-layer objects — keeping the
    presentation layer free from infrastructure imports.

    ``item_service_dep`` and ``category_service_dep`` are async generator
    functions (suitable for FastAPI ``Depends``).  For the SQLAlchemy backend
    they open one connection per request; for the in-memory backend they yield
    the shared singleton.
    """

    item_service_dep: Callable[[], AsyncGenerator[IItemApplicationService, None]]
    category_service_dep: Callable[[], AsyncGenerator[ICategoryApplicationService, None]]
    get_current_user: Callable[..., Coroutine[Any, Any, CurrentUser]]
    health_checks: list[IHealthCheck]


def get_app_state(request: Request) -> AppState:
    """Extract the typed AppState from the FastAPI request."""
    return request.app.state.app_state  # type: ignore[no-any-return]
