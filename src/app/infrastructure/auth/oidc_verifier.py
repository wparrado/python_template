"""Generic OIDC/OAuth2 JWT verifier.

Works with any OIDC-compliant provider (Keycloak, Auth0, Cognito, Google, etc.)
by reading OIDC_ISSUER and OIDC_AUDIENCE from the environment.

Flow:
  1. On startup: fetch JWKS from {OIDC_ISSUER}/.well-known/jwks.json
  2. Per-request: decode and verify the Bearer JWT using the cached JWKS
  3. Return CurrentUser or raise HTTPException(401)
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

import httpx
from authlib.jose import JsonWebKey, JsonWebToken, JWTClaims
from authlib.jose.errors import JoseError
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infrastructure.auth.models import CurrentUser
from app.settings import Settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


class OidcVerifier:
    """Validates Bearer JWTs against a provider's JWKS endpoint.

    Provider-agnostic: only OIDC_ISSUER and OIDC_AUDIENCE are required.
    Compatible with any standards-compliant OIDC provider.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jwks: dict[str, object] | None = None
        self._jwt = JsonWebToken(settings.oidc_algorithms)

    async def initialize(self) -> None:
        """Fetch JWKS from the discovery endpoint and cache them."""
        if not self._settings.oidc_issuer:
            logger.warning("OIDC_ISSUER not configured — auth is disabled")
            return
        jwks_url = f"{self._settings.oidc_issuer.rstrip('/')}/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10)
            response.raise_for_status()
            self._jwks = response.json()
        logger.info("JWKS loaded from %s", jwks_url)

    def verify_token(self, token: str) -> CurrentUser:
        """Decode and verify a JWT.  Returns CurrentUser or raises HTTPException(401)."""
        if not self._settings.oidc_issuer:
            # Auth disabled — return anonymous user for local dev
            return CurrentUser(sub="anonymous")
        if self._jwks is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth not ready")
        try:
            key = JsonWebKey.import_key_set(self._jwks)
            claims: JWTClaims = self._jwt.decode(token, key)
            claims.validate_iss()
            claims.validate_exp(now=None, leeway=0)
            claims.validate_aud()
            return CurrentUser(
                sub=str(claims.get("sub", "")),
                email=str(claims.get("email", "")),
                roles=list(claims.get("roles", claims.get("realm_access", {}).get("roles", []))),
                raw_claims=dict(claims),
            )
        except JoseError as exc:
            logger.warning("JWT validation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc


def make_current_user_dependency(verifier: OidcVerifier) -> Callable[..., Coroutine[Any, Any, CurrentUser]]:
    """Factory that creates a FastAPI dependency for the current authenticated user."""

    async def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = None,
    ) -> CurrentUser:
        if credentials is None:
            if not verifier._settings.oidc_issuer:
                return CurrentUser(sub="anonymous")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return verifier.verify_token(credentials.credentials)

    return get_current_user
