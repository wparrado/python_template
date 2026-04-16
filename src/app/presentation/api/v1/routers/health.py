"""Health check router.

GET /health        — liveness probe (always 200 if the process is running)
GET /health/ready  — readiness probe (checks infra dependencies)
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    service: str


@router.get("", response_model=HealthResponse, summary="Liveness probe")
async def liveness() -> HealthResponse:
    """Returns 200 as long as the process is running."""
    return HealthResponse(status="ok", service="app")


@router.get("/ready", response_model=HealthResponse, summary="Readiness probe")
async def readiness() -> HealthResponse:
    """Returns 200 when all infrastructure dependencies are ready.

    Extend this to check DB connectivity, cache availability, etc.
    """
    return HealthResponse(status="ready", service="app")
