"""OpenTelemetry tracing setup — OTLP exporter (provider-agnostic).

Set OTEL_EXPORTER_OTLP_ENDPOINT to point at any OTLP-compatible backend:
  - Jaeger:        http://jaeger:4317
  - Grafana Tempo: http://tempo:4317
  - Datadog Agent: http://datadog-agent:4317
  - AWS X-Ray:     use the ADOT collector
  - stdout:        set OTEL_ENABLED=false (console exporter used instead)
"""

from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

from app.settings import Settings

logger = logging.getLogger(__name__)


def configure_tracing(settings: Settings) -> trace.Tracer:
    """Configure the global TracerProvider.  Call once at application startup."""
    resource = Resource.create({SERVICE_NAME: settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_enabled:
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("OTLP tracing enabled → %s", settings.otel_exporter_otlp_endpoint)
    else:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        logger.info("OTLP tracing disabled — using console exporter")

    trace.set_tracer_provider(provider)
    return trace.get_tracer(settings.otel_service_name)
