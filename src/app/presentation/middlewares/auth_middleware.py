"""Auth middleware dependency — validates OIDC JWT and injects CurrentUser.

Used as a FastAPI dependency in protected routes:

    @router.get("/protected")
    async def protected(user: Annotated[CurrentUser, Depends(require_auth)]):
        ...
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infrastructure.auth.models import CurrentUser

_bearer = HTTPBearer(auto_error=False)


def make_auth_dependency(verify_token: Callable[[str], CurrentUser]) -> Callable[..., Coroutine[Any, Any, CurrentUser]]:
    """Return a FastAPI dependency that validates the Bearer token."""

    async def require_auth(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    ) -> CurrentUser:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return verify_token(credentials.credentials)

    return require_auth
