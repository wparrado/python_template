"""Health check router.

GET /health        — liveness probe (always 200 if the process is running)
GET /health/ready  — readiness probe (checks all registered infra dependencies)
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.presentation.app_state import get_app_state

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    service: str


class ReadinessResponse(BaseModel):
    """Readiness check response with per-dependency details."""

    status: str
    service: str
    checks: dict[str, str]


@router.get("", response_model=HealthResponse, summary="Liveness probe")
async def liveness() -> HealthResponse:
    """Returns 200 as long as the process is running."""
    return HealthResponse(status="ok", service="app")


@router.get("/ready", summary="Readiness probe")
async def readiness(request: Request) -> JSONResponse:
    """Returns 200 when all infrastructure dependencies are healthy, 503 otherwise.

    Each registered IHealthCheck is executed and its result included in the
    response body so operators can identify which dependency is failing.
    """
    health_checks = get_app_state(request).health_checks
    results: dict[str, str] = {}
    all_healthy = True

    for check in health_checks:
        health_status = await check.check()
        results[health_status.name] = "ok" if health_status.healthy else f"fail: {health_status.detail}"
        if not health_status.healthy:
            all_healthy = False

    http_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content=ReadinessResponse(
            status="ready" if all_healthy else "degraded",
            service="app",
            checks=results,
        ).model_dump(),
    )
