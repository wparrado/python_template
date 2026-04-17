"""End-to-end async integration tests for the Categories API.

Verifies the complete request lifecycle using ``httpx.AsyncClient``:

    HTTP request (httpx)
      → FastAPI routing
      → presentation layer (schema validation, auth bypass)
      → application layer (command/query handlers)
      → domain layer (aggregate, invariants, events)
      → infrastructure layer (in-memory repository)
      → HTTP response

Nothing is mocked — every layer participates.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.settings import Settings


@pytest.fixture
def app():
    """FastAPI application wired with in-memory adapters."""
    settings = Settings(app_name="e2e-test", debug=False, oidc_issuer="", otel_enabled=False)
    return create_app(settings=settings)


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client bound to the test app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Full lifecycle — sequential scenario
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_category_full_lifecycle(client: AsyncClient) -> None:
    """POST → GET → PUT → DELETE → GET (404): the complete CRUD lifecycle."""

    # 1. Create
    create_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Lifecycle Category", "slug": "lifecycle-category", "description": "E2E test"},
    )
    assert create_resp.status_code == 201, create_resp.text
    cat = create_resp.json()
    cat_id = cat["id"]
    assert cat["name"] == "Lifecycle Category"
    assert cat["slug"] == "lifecycle-category"
    assert "created_at" in cat
    assert "updated_at" in cat

    # 2. Read — category must be retrievable immediately after creation
    get_resp = await client.get(f"/api/v1/categories/{cat_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == cat_id

    # 3. Update — name changes, slug is preserved
    update_resp = await client.put(
        f"/api/v1/categories/{cat_id}",
        json={"name": "Updated Category"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "Updated Category"
    assert updated["description"] == "E2E test"  # description unchanged

    # 4. Delete
    delete_resp = await client.delete(f"/api/v1/categories/{cat_id}")
    assert delete_resp.status_code == 204

    # 5. Verify deleted — category must no longer be accessible
    gone_resp = await client.get(f"/api/v1/categories/{cat_id}")
    assert gone_resp.status_code == 404


@pytest.mark.asyncio
async def test_created_category_appears_in_list(client: AsyncClient) -> None:
    """Categories created via POST must appear in GET /categories."""
    await client.post("/api/v1/categories", json={"name": "Alpha", "slug": "alpha"})
    await client.post("/api/v1/categories", json={"name": "Beta", "slug": "beta"})

    list_resp = await client.get("/api/v1/categories")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 2
    names = {c["name"] for c in data["items"]}
    assert names == {"Alpha", "Beta"}


@pytest.mark.asyncio
async def test_deleted_category_excluded_from_list(client: AsyncClient) -> None:
    """Deleted categories must not appear in GET /categories."""
    await client.post("/api/v1/categories", json={"name": "Keep", "slug": "keep"})
    r2 = await client.post("/api/v1/categories", json={"name": "Remove", "slug": "remove"})

    await client.delete(f"/api/v1/categories/{r2.json()['id']}")

    list_resp = await client.get("/api/v1/categories")
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["items"][0]["name"] == "Keep"


@pytest.mark.asyncio
async def test_search_reflects_updates(client: AsyncClient) -> None:
    """Updated category name must be discoverable via search immediately."""
    created = (await client.post("/api/v1/categories", json={"name": "Old Name", "slug": "old-name"})).json()

    await client.put(f"/api/v1/categories/{created['id']}", json={"name": "New Name"})

    search_resp = await client.get("/api/v1/categories/search?name_contains=new")
    assert search_resp.status_code == 200
    items = search_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "New Name"
