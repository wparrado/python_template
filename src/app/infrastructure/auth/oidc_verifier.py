"""Generic OIDC/OAuth2 JWT verifier.

Works with any OIDC-compliant provider (Keycloak, Auth0, Cognito, Google, etc.)
by reading OIDC_ISSUER and OIDC_AUDIENCE from the environment.

Flow:
  1. On startup: fetch JWKS from {OIDC_ISSUER}/.well-known/jwks.json
     The outbound HTTP call is protected by a circuit breaker.
  2. Per-request: decode and verify the Bearer JWT using the cached JWKS
  3. Return CurrentUser or raise HTTPException(401)
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

import httpx
import pybreaker
from authlib.jose import JsonWebKey, JsonWebToken, JWTClaims
from authlib.jose.errors import JoseError
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.ports.outbound.circuit_breaker import ICircuitBreaker
from app.infrastructure.auth.models import CurrentUser
from app.settings import Settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


class OidcVerifier:
    """Validates Bearer JWTs against a provider's JWKS endpoint.

    Provider-agnostic: only OIDC_ISSUER and OIDC_AUDIENCE are required.
    Compatible with any standards-compliant OIDC provider.
    An optional ICircuitBreaker guards the outbound JWKS HTTP call.
    """

    def __init__(self, settings: Settings, circuit_breaker: ICircuitBreaker | None = None) -> None:
        self._settings = settings
        self._jwks: dict[str, object] | None = None
        self._jwt = JsonWebToken(settings.oidc_algorithms)
        self._circuit_breaker = circuit_breaker

    @property
    def oidc_issuer(self) -> str:
        """Return the configured OIDC issuer URL."""
        return self._settings.oidc_issuer

    async def initialize(self) -> None:
        """Fetch JWKS from the discovery endpoint and cache them."""
        if not self._settings.oidc_issuer:
            logger.warning("OIDC_ISSUER not configured — auth is disabled")
            return
        jwks_url = f"{self._settings.oidc_issuer.rstrip('/')}/.well-known/jwks.json"
        try:
            self._jwks = await self._fetch_jwks(jwks_url)
        except pybreaker.CircuitBreakerError as exc:
            logger.error("Circuit breaker OPEN — cannot fetch JWKS from %s: %s", jwks_url, exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service unavailable (circuit open)",
            ) from exc
        logger.info("JWKS loaded from %s", jwks_url)

    async def _fetch_jwks(self, jwks_url: str) -> dict[str, object]:
        """Fetch JWKS, optionally through the circuit breaker."""

        def _sync_fetch() -> dict[str, object]:
            with httpx.Client() as client:
                response = client.get(jwks_url, timeout=10)
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

        if self._circuit_breaker is not None:
            return self._circuit_breaker.call(_sync_fetch)  # type: ignore[no-any-return]

        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

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
            if not verifier.oidc_issuer:
                return CurrentUser(sub="anonymous")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return verifier.verify_token(credentials.credentials)

    return get_current_user
