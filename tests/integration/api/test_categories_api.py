"""HTTP-level integration tests for the Categories API.

These tests exercise the full request/response cycle using FastAPI's
TestClient — from HTTP method through presentation, application, and
infrastructure layers — ensuring all layers are wired correctly.
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
# POST /api/v1/categories
# ---------------------------------------------------------------------------


def test_create_category_returns_201(client: TestClient) -> None:
    response = client.post(
        "/api/v1/categories",
        json={"name": "Electronics", "description": "Electronic devices"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Electronics"
    assert data["description"] == "Electronic devices"
    assert "id" in data
    assert "slug" in data


def test_create_category_derives_slug_from_name(client: TestClient) -> None:
    response = client.post("/api/v1/categories", json={"name": "Home Appliances"})
    assert response.status_code == 201
    assert response.json()["slug"] == "home-appliances"


def test_create_category_accepts_explicit_slug(client: TestClient) -> None:
    response = client.post(
        "/api/v1/categories",
        json={"name": "My Category", "slug": "my-custom-slug"},
    )
    assert response.status_code == 201
    assert response.json()["slug"] == "my-custom-slug"


def test_create_category_empty_name_returns_422(client: TestClient) -> None:
    response = client.post("/api/v1/categories", json={"name": ""})
    assert response.status_code == 422


def test_create_category_missing_name_returns_422(client: TestClient) -> None:
    response = client.post("/api/v1/categories", json={"description": "No name"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/categories
# ---------------------------------------------------------------------------


def test_list_categories_empty_returns_200(client: TestClient) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["has_next"] is False
    assert data["has_previous"] is False


def test_list_categories_pagination(client: TestClient) -> None:
    for i in range(5):
        client.post("/api/v1/categories", json={"name": f"Category {i}", "slug": f"category-{i}"})
    response = client.get("/api/v1/categories?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2


def test_list_categories_has_next(client: TestClient) -> None:
    for i in range(3):
        client.post("/api/v1/categories", json={"name": f"Cat {i}", "slug": f"cat-{i}"})
    response = client.get("/api/v1/categories?limit=2&offset=0")
    assert response.json()["has_next"] is True


def test_list_categories_invalid_limit_returns_422(client: TestClient) -> None:
    response = client.get("/api/v1/categories?limit=0")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/categories/{id}
# ---------------------------------------------------------------------------


def test_get_category_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/categories", json={"name": "Books", "slug": "books"}).json()
    response = client.get(f"/api/v1/categories/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["name"] == "Books"


def test_get_category_not_found_returns_404(client: TestClient) -> None:
    import uuid
    response = client.get(f"/api/v1/categories/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_category_invalid_uuid_returns_422(client: TestClient) -> None:
    response = client.get("/api/v1/categories/not-a-uuid")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/categories/search
# ---------------------------------------------------------------------------


def test_search_categories_by_name(client: TestClient) -> None:
    client.post("/api/v1/categories", json={"name": "Electronics", "slug": "electronics"})
    client.post("/api/v1/categories", json={"name": "Furniture", "slug": "furniture"})
    response = client.get("/api/v1/categories/search?name_contains=elec")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Electronics"


def test_search_categories_by_slug(client: TestClient) -> None:
    client.post("/api/v1/categories", json={"name": "Sports", "slug": "sports"})
    client.post("/api/v1/categories", json={"name": "Other", "slug": "other"})
    response = client.get("/api/v1/categories/search?slug=sports")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "sports"


def test_search_no_results_returns_empty(client: TestClient) -> None:
    response = client.get("/api/v1/categories/search?name_contains=zzznomatch")
    assert response.status_code == 200
    assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# PUT /api/v1/categories/{id}
# ---------------------------------------------------------------------------


def test_update_category_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/categories", json={"name": "Old Name", "slug": "old-name"}).json()
    response = client.put(
        f"/api/v1/categories/{created['id']}",
        json={"name": "New Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_update_category_preserves_unchanged_fields(client: TestClient) -> None:
    created = client.post(
        "/api/v1/categories",
        json={"name": "My Cat", "slug": "my-cat", "description": "My description"},
    ).json()
    response = client.put(
        f"/api/v1/categories/{created['id']}",
        json={"name": "My Cat Updated"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["description"] == "My description"


def test_update_category_not_found_returns_404(client: TestClient) -> None:
    import uuid
    response = client.put(
        f"/api/v1/categories/{uuid.uuid4()}",
        json={"name": "Ghost"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/categories/{id}
# ---------------------------------------------------------------------------


def test_delete_category_returns_204(client: TestClient) -> None:
    created = client.post("/api/v1/categories", json={"name": "ToDelete", "slug": "to-delete"}).json()
    response = client.delete(f"/api/v1/categories/{created['id']}")
    assert response.status_code == 204


def test_delete_category_idempotent(client: TestClient) -> None:
    import uuid
    response = client.delete(f"/api/v1/categories/{uuid.uuid4()}")
    assert response.status_code == 204


def test_deleted_category_not_found_on_get(client: TestClient) -> None:
    created = client.post("/api/v1/categories", json={"name": "Gone", "slug": "gone"}).json()
    client.delete(f"/api/v1/categories/{created['id']}")
    response = client.get(f"/api/v1/categories/{created['id']}")
    assert response.status_code == 404
