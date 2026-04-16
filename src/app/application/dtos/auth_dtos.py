"""Auth DTOs — application-layer data models for authentication context.

These are the ONLY auth-related types the presentation layer should use.
Infrastructure adapters (OIDC verifier, API key validator, etc.) produce
these types; the domain has zero knowledge of authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated user extracted from a validated credential (e.g., OIDC JWT)."""

    sub: str
    email: str = ""
    roles: list[str] = field(default_factory=list)
    raw_claims: dict[str, object] = field(default_factory=dict, repr=False)
