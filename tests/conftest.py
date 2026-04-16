"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_name="test-app",
        debug=True,
        oidc_issuer="",
        otel_enabled=False,
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    app = create_app(settings=test_settings)
    with TestClient(app) as c:
        yield c
