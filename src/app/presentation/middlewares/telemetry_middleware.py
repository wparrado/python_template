"""Telemetry middleware — enriches active span with HTTP attributes."""

from __future__ import annotations

from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware that enriches active OpenTelemetry spans with HTTP request attributes."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        span = trace.get_current_span()
        if span.is_recording():
            correlation_id = getattr(request.state, "correlation_id", None)
            if correlation_id:
                span.set_attribute("correlation_id", correlation_id)
            span.set_attribute("http.route", request.url.path)

        response = await call_next(request)

        if span.is_recording():
            span.set_attribute("http.status_code", response.status_code)

        return response
