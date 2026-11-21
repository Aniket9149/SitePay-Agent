#Owner::ANIKET::ANHOTRA = MR.Panda
"""Full test from registration to logout, including token rotation and theft handling."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("httpx")

from conftest import auth_headers, register_user  # noqa: E402


def test_register_login_me_logout_flow(client) -> None:  # type: ignore[no-untyped-def]
    """A new user registers, logs in, reads their profile and logs out."""
    registration = register_user(client, "owner@example.com")
    assert registration["organization"]["role"] == "owner"
    assert "password" not in str(registration).lower().replace("password_hash", "")

    login = client.post(
        "/api/v1/auth/login", json={"email": "OWNER@example.com", "password": "strongpass123"}
    )
    assert login.status_code == 200
    tokens = login.json()

    me = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + tokens["access_token"]})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "owner@example.com"
    assert len(me.json()["organizations"]) == 1

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 204
    again = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401


def test_wrong_password_and_unknown_email_give_the_same_error(client) -> None:  # type: ignore[no-untyped-def]
    """Login failures must not reveal whether the email exists."""
    register_user(client, "owner@example.com")
    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "owner@example.com", "password": "wrong-password-1"}
    )
    unknown_email = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password-1"}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_duplicate_email_and_weak_password_are_rejected(client) -> None:  # type: ignore[no-untyped-def]
    """The same email cannot register twice, and weak passwords are refused."""
    register_user(client, "owner@example.com")
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "Owner@Example.com", "password": "strongpass123", "name": "X",
              "organization_name": "Y"},
    )
    assert duplicate.status_code == 409
    weak = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "short", "name": "X", "organization_name": "Y"},
    )
    assert weak.status_code == 422


def test_protected_routes_need_a_valid_access_token(client) -> None:  # type: ignore[no-untyped-def]
    """No token, a garbage token and a refresh token are all refused."""
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    registration = register_user(client, "owner@example.com")
    refresh_as_access = {"Authorization": "Bearer " + registration["tokens"]["refresh_token"]}
    assert client.get("/api/v1/auth/me", headers=refresh_as_access).status_code == 401


def test_refresh_rotates_and_reuse_revokes_everything(client) -> None:  # type: ignore[no-untyped-def]
    """Each refresh token works once. Reusing an old one revokes the whole family."""
    registration = register_user(client, "owner@example.com")
    first_refresh = registration["tokens"]["refresh_token"]
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert rotated.status_code == 200
    second_refresh = rotated.json()["refresh_token"]
    assert second_refresh != first_refresh

    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert replay.status_code == 401
    after_theft = client.post("/api/v1/auth/refresh", json={"refresh_token": second_refresh})
    assert after_theft.status_code == 401


def test_health_routes(client) -> None:  # type: ignore[no-untyped-def]
    """Liveness and readiness both answer, and security headers are present."""
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.headers["x-content-type-options"] == "nosniff"


def test_audit_chain_is_intact_and_immutable(client, session_factory) -> None:  # type: ignore[no-untyped-def]
    """Actions create audit records that verify, and the database refuses edits."""
    from sqlalchemy import text
    from sqlalchemy.exc import DatabaseError

    from app.errors import AuditLogImmutableError
    from app.models.audit_log_model import AuditLogEntry
    from app.services.audit_service import find_broken_audit_position

    registration = register_user(client, "owner@example.com")
    organization_id = registration["organization"]["id"]
    client.post(
        f"/api/v1/organizations/{organization_id}/projects",
        json={"name": "Tower A", "contract_value": "1250000.50"},
        headers=auth_headers(registration),
    )
    with session_factory() as session:
        assert find_broken_audit_position(session, organization_id) is None
        entries = session.query(AuditLogEntry).filter_by(chain_scope=organization_id).all()
        assert {entry.action for entry in entries} >= {"user.registered", "project.created"}

        entries[0].action = "tampered"
        with pytest.raises(AuditLogImmutableError):
            session.flush()
        session.rollback()

        with pytest.raises(DatabaseError, match="append only"):
            session.execute(text("UPDATE audit_logs SET action = 'x'"))
        session.rollback()
        with pytest.raises(DatabaseError, match="append only"):
            session.execute(text("DELETE FROM audit_logs"))
        session.rollback()


def test_login_is_locked_after_repeated_failures_even_with_the_right_password(client) -> None:  # type: ignore[no-untyped-def]
    """Five wrong passwords lock the login. Then even the correct password is refused."""
    register_user(client, "owner@example.com")
    wrong = {"email": "owner@example.com", "password": "wrong-password-1"}
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json=wrong).status_code == 401
    locked = client.post("/api/v1/auth/login", json=wrong)
    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) >= 1
    assert locked.json()["error"]["code"] == "rate_limited"
    correct = client.post(
        "/api/v1/auth/login", json={"email": "owner@example.com", "password": "strongpass123"}
    )
    assert correct.status_code == 429


def test_registration_is_limited_per_address(client) -> None:  # type: ignore[no-untyped-def]
    """The eleventh registration from one address in an hour is refused."""
    for number in range(10):
        register_user(client, f"user{number}@example.com", f"Company {number}")
    blocked = client.post(
        "/api/v1/auth/register",
        json={"email": "user11@example.com", "password": "strongpass123", "name": "X",
              "organization_name": "Company 11"},
    )
    assert blocked.status_code == 429


def test_a_faked_forwarded_header_does_not_dodge_the_limit(client) -> None:  # type: ignore[no-untyped-def]
    """With no trusted proxy configured, X-Forwarded-For is ignored, so changing it changes nothing."""
    register_user(client, "owner@example.com")
    for number in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "wrong-password-1"},
            headers={"X-Forwarded-For": f"10.0.0.{number}"},
        )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "strongpass123"},
        headers={"X-Forwarded-For": "10.9.9.9"},
    )
    assert response.status_code == 429
