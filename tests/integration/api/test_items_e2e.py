"""End-to-end async integration tests for the Items API.

Verifies the complete request lifecycle using ``httpx.AsyncClient``:

    HTTP request (httpx)
      → FastAPI routing
      → presentation layer (schema validation, auth bypass)
      → application layer (command/query handlers)
      → domain layer (aggregate, invariants, events)
      → infrastructure layer (in-memory repository)
      → HTTP response

Unlike unit tests, nothing is mocked — every layer participates.
The backend is the in-memory adapter so no external services are needed.

The core scenario (``test_item_full_lifecycle``) exercises the canonical
CRUD flow as a single ordered sequence to ensure state transitions are
consistent across operations.
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
async def test_item_full_lifecycle(client: AsyncClient) -> None:
    """POST → GET → PUT → DELETE → GET (404): the complete CRUD lifecycle."""

    # 1. Create
    create_resp = await client.post(
        "/api/v1/items",
        json={"name": "Lifecycle Widget", "price": "19.99", "description": "E2E test item"},
    )
    assert create_resp.status_code == 201, create_resp.text
    item = create_resp.json()
    item_id = item["id"]
    assert item["name"] == "Lifecycle Widget"
    assert float(item["price"]) == 19.99
    assert "created_at" in item
    assert "updated_at" in item

    # 2. Read — item must be retrievable immediately after creation
    get_resp = await client.get(f"/api/v1/items/{item_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == item_id

    # 3. Update — name changes, price is preserved
    update_resp = await client.put(
        f"/api/v1/items/{item_id}",
        json={"name": "Updated Widget"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "Updated Widget"
    assert float(updated["price"]) == 19.99  # price unchanged

    # 4. Delete
    delete_resp = await client.delete(f"/api/v1/items/{item_id}")
    assert delete_resp.status_code == 204

    # 5. Verify deleted — item must no longer be accessible
    gone_resp = await client.get(f"/api/v1/items/{item_id}")
    assert gone_resp.status_code == 404


# ---------------------------------------------------------------------------
# Isolation — each test gets a fresh app instance via the fixture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_created_item_appears_in_list(client: AsyncClient) -> None:
    """Items created via POST must appear in GET /items."""
    await client.post("/api/v1/items", json={"name": "Alpha", "price": "1.00"})
    await client.post("/api/v1/items", json={"name": "Beta", "price": "2.00"})

    list_resp = await client.get("/api/v1/items")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 2
    names = {i["name"] for i in data["items"]}
    assert names == {"Alpha", "Beta"}


@pytest.mark.asyncio
async def test_deleted_item_excluded_from_list(client: AsyncClient) -> None:
    """Deleted items must not appear in GET /items."""
    await client.post("/api/v1/items", json={"name": "Keep", "price": "1.00"})
    r2 = await client.post("/api/v1/items", json={"name": "Remove", "price": "1.00"})

    await client.delete(f"/api/v1/items/{r2.json()['id']}")

    list_resp = await client.get("/api/v1/items")
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["items"][0]["name"] == "Keep"


@pytest.mark.asyncio
async def test_search_reflects_updates(client: AsyncClient) -> None:
    """Updated item name must be discoverable via search immediately."""
    created = (await client.post("/api/v1/items", json={"name": "Old Name", "price": "5.00"})).json()

    await client.put(f"/api/v1/items/{created['id']}", json={"name": "New Name"})

    search_resp = await client.get("/api/v1/items/search?name_contains=new")
    assert search_resp.status_code == 200
    items = search_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "New Name"
