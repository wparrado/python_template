"""OpenTelemetry metrics setup — OTLP exporter (provider-agnostic)."""

from __future__ import annotations

import logging

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from app.settings import Settings

logger = logging.getLogger(__name__)


def configure_metrics(settings: Settings) -> metrics.Meter:
    """Configure the global MeterProvider.  Call once at application startup."""
    resource = Resource.create({SERVICE_NAME: settings.otel_service_name})

    if settings.otel_enabled:
        exporter: OTLPMetricExporter | ConsoleMetricExporter = OTLPMetricExporter(
            endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
        )
        logger.info("OTLP metrics enabled → %s", settings.otel_exporter_otlp_endpoint)
    else:
        exporter = ConsoleMetricExporter()

    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=30_000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    meter = metrics.get_meter(settings.otel_service_name)

    # Pre-build standard instruments available globally
    meter.create_counter("http_requests_total", description="Total HTTP requests")
    meter.create_histogram("http_request_duration_seconds", description="HTTP request duration in seconds")

    return meter
