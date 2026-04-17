"""Architectural dependency tests using pytest-archon.

These tests enforce the hexagonal architecture dependency rules:

  domain      → imports nothing from application, infrastructure, presentation
  application → imports nothing from infrastructure, presentation
  presentation → imports nothing from domain model directly

  External frameworks (sqlalchemy, fastapi) must not leak into domain or
  application layers.  Infrastructure must not import fastapi (presentation
  concern); presentation must not import sqlalchemy (infrastructure concern).

Run:
    uv run pytest tests/architecture/ -v
"""

from __future__ import annotations

from pytest_archon import archrule


def test_domain_does_not_import_application() -> None:
    """Domain layer must not import from application layer."""
    (
        archrule("domain-independence-from-application")
        .match("app.domain.*")
        .should_not_import("app.application")
        .check("app")
    )


def test_domain_does_not_import_infrastructure() -> None:
    """Domain layer must not import from infrastructure layer."""
    (
        archrule("domain-independence-from-infrastructure")
        .match("app.domain.*")
        .should_not_import("app.infrastructure")
        .check("app")
    )


def test_domain_does_not_import_presentation() -> None:
    """Domain layer must not import from presentation layer."""
    (
        archrule("domain-independence-from-presentation")
        .match("app.domain.*")
        .should_not_import("app.presentation")
        .check("app")
    )


def test_application_does_not_import_infrastructure() -> None:
    """Application layer must not import from infrastructure layer."""
    (
        archrule("application-independence-from-infrastructure")
        .match("app.application.*")
        .should_not_import("app.infrastructure")
        .check("app")
    )


def test_application_does_not_import_presentation() -> None:
    """Application layer must not import from presentation layer."""
    (
        archrule("application-independence-from-presentation")
        .match("app.application.*")
        .should_not_import("app.presentation")
        .check("app")
    )


def test_presentation_does_not_import_domain_model() -> None:
    """Presentation must not directly access domain model (only via DTOs)."""
    (
        archrule("presentation-no-direct-domain-model")
        .match("app.presentation.*")
        .should_not_import("app.domain.model")
        .check("app")
    )


# ---------------------------------------------------------------------------
# External framework isolation
# ---------------------------------------------------------------------------


def test_domain_does_not_import_sqlalchemy() -> None:
    """Domain layer must not depend on SQLAlchemy (persistence is infrastructure)."""
    (
        archrule("domain-no-sqlalchemy")
        .match("app.domain.*")
        .should_not_import("sqlalchemy")
        .check("app")
    )


def test_domain_does_not_import_fastapi() -> None:
    """Domain layer must not depend on FastAPI (HTTP is presentation)."""
    (
        archrule("domain-no-fastapi")
        .match("app.domain.*")
        .should_not_import("fastapi")
        .check("app")
    )


def test_application_does_not_import_sqlalchemy() -> None:
    """Application layer must not depend on SQLAlchemy."""
    (
        archrule("application-no-sqlalchemy")
        .match("app.application.*")
        .should_not_import("sqlalchemy")
        .check("app")
    )


def test_application_does_not_import_fastapi() -> None:
    """Application layer must not depend on FastAPI."""
    (
        archrule("application-no-fastapi")
        .match("app.application.*")
        .should_not_import("fastapi")
        .check("app")
    )


def test_presentation_does_not_import_sqlalchemy() -> None:
    """Presentation layer must not depend on SQLAlchemy (reads go via application ports)."""
    (
        archrule("presentation-no-sqlalchemy")
        .match("app.presentation.*")
        .should_not_import("sqlalchemy")
        .check("app")
    )
