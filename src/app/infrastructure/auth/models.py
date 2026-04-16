"""CurrentUser dataclass — lives in infrastructure, NOT in domain.

The domain has zero knowledge of authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated user extracted from a validated OIDC JWT."""

    sub: str
    email: str = ""
    roles: list[str] = field(default_factory=list)
    raw_claims: dict[str, object] = field(default_factory=dict, repr=False)
