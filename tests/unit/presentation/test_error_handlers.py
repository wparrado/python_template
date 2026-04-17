"""Unit tests for the presentation error handlers.

Verifies that domain errors are translated to the correct HTTP status
codes and response shapes by ``register_error_handlers``.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.exceptions import (
    ConflictError,
    DomainError,
    ItemNotFoundError,
    NotFoundError,
    ValidationError,
)
from app.presentation.error_handlers import register_error_handlers


@pytest.fixture
def error_app() -> FastAPI:
    """Minimal FastAPI app with error handlers registered and one route per exception."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/item-not-found")
    async def raise_item_not_found() -> None:
        raise ItemNotFoundError("item-123")

    @app.get("/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError("resource-xyz")

    @app.get("/validation")
    async def raise_validation() -> None:
        raise ValidationError("price must be positive")

    @app.get("/conflict")
    async def raise_conflict() -> None:
        raise ConflictError("slug already taken")

    @app.get("/domain-error")
    async def raise_domain_error() -> None:
        raise DomainError("something went wrong in the domain")

    return app


@pytest.fixture
def client(error_app: FastAPI) -> TestClient:
    return TestClient(error_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# ItemNotFoundError → 404
# ---------------------------------------------------------------------------


def test_item_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/item-not-found")
    assert response.status_code == 404


def test_item_not_found_response_shape(client: TestClient) -> None:
    response = client.get("/item-not-found")
    body = response.json()
    assert "detail" in body
    assert "item-123" in body["detail"]


# ---------------------------------------------------------------------------
# NotFoundError → 404
# ---------------------------------------------------------------------------


def test_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/not-found")
    assert response.status_code == 404


def test_not_found_response_shape(client: TestClient) -> None:
    body = client.get("/not-found").json()
    assert "detail" in body
    assert "resource-xyz" in body["detail"]


# ---------------------------------------------------------------------------
# ValidationError → 422
# ---------------------------------------------------------------------------


def test_validation_error_returns_422(client: TestClient) -> None:
    response = client.get("/validation")
    assert response.status_code == 422


def test_validation_error_response_shape(client: TestClient) -> None:
    body = client.get("/validation").json()
    assert "detail" in body
    assert "price must be positive" in body["detail"]


# ---------------------------------------------------------------------------
# ConflictError → 409
# ---------------------------------------------------------------------------


def test_conflict_returns_409(client: TestClient) -> None:
    response = client.get("/conflict")
    assert response.status_code == 409


def test_conflict_response_shape(client: TestClient) -> None:
    body = client.get("/conflict").json()
    assert "detail" in body
    assert "slug already taken" in body["detail"]


# ---------------------------------------------------------------------------
# DomainError (base) → 400
# ---------------------------------------------------------------------------


def test_domain_error_returns_400(client: TestClient) -> None:
    response = client.get("/domain-error")
    assert response.status_code == 400


def test_domain_error_response_shape(client: TestClient) -> None:
    body = client.get("/domain-error").json()
    assert "detail" in body
    assert "something went wrong in the domain" in body["detail"]
