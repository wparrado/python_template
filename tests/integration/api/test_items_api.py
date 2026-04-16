"""HTTP-level integration tests for the Items API.

These tests exercise the full request/response cycle using FastAPI's
TestClient — from HTTP method through presentation, application, and
infrastructure layers — ensuring all layers are wired correctly.

Unlike unit tests, these tests verify integration contracts:
  - Correct HTTP status codes for each operation
  - JSON response shapes match the declared response models
  - Domain errors propagate and are translated to the right HTTP codes
  - CRUD lifecycle works end-to-end
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh app instance with test settings."""
    settings = Settings(app_name="test-app", debug=False, oidc_issuer="", otel_enabled=False)
    return TestClient(create_app(settings=settings), raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# POST /api/v1/items
# ---------------------------------------------------------------------------


def test_create_item_returns_201(client: TestClient) -> None:
    response = client.post("/api/v1/items", json={"name": "Widget", "price": 9.99})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Widget"
    assert data["price"] == 9.99
    assert "id" in data


def test_create_item_empty_name_returns_422(client: TestClient) -> None:
    response = client.post("/api/v1/items", json={"name": "", "price": 9.99})
    assert response.status_code == 422


def test_create_item_negative_price_returns_422(client: TestClient) -> None:
    response = client.post("/api/v1/items", json={"name": "Widget", "price": -1.0})
    assert response.status_code == 422


def test_create_item_missing_fields_returns_422(client: TestClient) -> None:
    response = client.post("/api/v1/items", json={"name": "Widget"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/items
# ---------------------------------------------------------------------------


def test_list_items_empty_returns_200(client: TestClient) -> None:
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    assert response.json() == []


def test_list_items_returns_created_items(client: TestClient) -> None:
    client.post("/api/v1/items", json={"name": "A", "price": 1.0})
    client.post("/api/v1/items", json={"name": "B", "price": 2.0})
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# GET /api/v1/items/{item_id}
# ---------------------------------------------------------------------------


def test_get_item_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/items", json={"name": "Gadget", "price": 49.99}).json()
    response = client.get(f"/api/v1/items/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["name"] == "Gadget"


def test_get_item_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/items/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/items/{item_id}
# ---------------------------------------------------------------------------


def test_update_item_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/items", json={"name": "Old Name", "price": 5.0}).json()
    response = client.put(f"/api/v1/items/{created['id']}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["price"] == 5.0


def test_update_item_not_found_returns_404(client: TestClient) -> None:
    response = client.put(
        "/api/v1/items/00000000-0000-0000-0000-000000000000",
        json={"name": "X"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/items/{item_id}
# ---------------------------------------------------------------------------


def test_delete_item_returns_204(client: TestClient) -> None:
    created = client.post("/api/v1/items", json={"name": "ToDelete", "price": 1.0}).json()
    response = client.delete(f"/api/v1/items/{created['id']}")
    assert response.status_code == 204


def test_delete_item_then_get_returns_404(client: TestClient) -> None:
    created = client.post("/api/v1/items", json={"name": "ToDelete", "price": 1.0}).json()
    client.delete(f"/api/v1/items/{created['id']}")
    response = client.get(f"/api/v1/items/{created['id']}")
    assert response.status_code == 404


def test_delete_item_not_found_returns_404(client: TestClient) -> None:
    response = client.delete("/api/v1/items/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
