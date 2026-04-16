"""CurrentUser — re-exported from the application layer for backwards compatibility.

Infrastructure code should import CurrentUser from:
    app.application.dtos.auth_dtos

This file is kept to avoid breaking any existing infrastructure code that
imports from this location directly.
"""

from __future__ import annotations

from app.application.dtos.auth_dtos import CurrentUser

__all__ = ["CurrentUser"]
