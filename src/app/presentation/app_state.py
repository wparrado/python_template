"""Typed application state container.

FastAPI's ``app.state`` is an untyped namespace by default.  This module
provides a strongly-typed wrapper so that router code can access state
members without ``# type: ignore`` suppressions.

Usage (in a router):
    from app.presentation.app_state import get_app_state

    def _get_service(request: Request) -> IItemApplicationService:
        return get_app_state(request).item_service
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.application.services.item_service import ItemApplicationService


@dataclass
class AppState:
    """Typed snapshot of presentation-relevant ``app.state`` fields.

    Only holds references to application-layer objects — keeping the
    presentation layer free from infrastructure imports.
    """

    item_service: ItemApplicationService


def get_app_state(request: Request) -> AppState:
    """Extract the typed AppState from the FastAPI request."""
    return request.app.state.app_state  # type: ignore[no-any-return]
