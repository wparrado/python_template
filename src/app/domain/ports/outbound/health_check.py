"""Redirect — IHealthCheck moved to the application layer.

Health verification is an operational concern orchestrated by the
application, not a business rule of the domain.

Import from the canonical location::

    from app.application.ports.health_check import HealthStatus, IHealthCheck
"""
