#Owner::ANIKET::ANHOTRA = MR.Panda
"""Shared test setup.

Integration fixtures import FastAPI, SQLAlchemy and httpx inside the fixture, so the
unit tests still run in environments that do not have those packages. Integration tests
are skipped, never silently passed, when the packages are missing.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from app.config import Settings, load_settings

TEST_SECRET_KEY = "test-secret-key-that-is-long-enough-1234567890"


@pytest.fixture()
def test_settings() -> Settings:
    """Settings for tests: in memory SQLite and a fixed, long secret key.

    Built through load_settings so the real validation rules apply.
    """
    return load_settings(
        {
            "APPLICATION_ENVIRONMENT": "development",
            "DATABASE_URL": "sqlite://",
            "SECRET_KEY": TEST_SECRET_KEY,
        }
    )


@pytest.fixture()
def session_factory(test_settings: Settings) -> Iterator[Any]:
    """Create an in memory database with all tables and the audit triggers.

    Skips the test when SQLAlchemy is not installed.
    """
    pytest.importorskip("sqlalchemy")
    from app.database import build_engine, build_session_factory
    from app.database_triggers import audit_trigger_statements
    from app.models import Base

    engine = build_engine(test_settings.database_url)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for statement in audit_trigger_statements("sqlite"):
            connection.exec_driver_sql(statement)
    yield build_session_factory(engine)
    engine.dispose()


@pytest.fixture()
def client(test_settings: Settings, session_factory: Any) -> Iterator[Any]:
    """A test client for the full application on the in memory database.

    Skips the test when FastAPI or httpx is not installed.
    """
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from app.main import create_application

    application = create_application(test_settings, session_factory)
    with TestClient(application) as test_client:
        yield test_client


def register_user(client: Any, email: str, organization_name: str = "Test Builders") -> dict[str, Any]:
    """Register a user through the API and return the response body.

    Fails the test immediately if registration does not succeed.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "strongpass123",
            "name": "Test User",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def auth_headers(registration_body: dict[str, Any]) -> dict[str, str]:
    """Build the Authorization header from a registration or login response.

    Uses the access token.
    """
    return {"Authorization": "Bearer " + registration_body["tokens"]["access_token"]}
