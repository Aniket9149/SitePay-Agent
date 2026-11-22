#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tests for request formats, and the audit append-only triggers run on real SQLite."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.database_triggers import (
    audit_trigger_drop_statements,
    audit_trigger_statements,
)
from app.schemas.auth_schema import LoginRequest, RegisterRequest
from app.schemas.organization_schema import MemberAddRequest
from app.schemas.project_schema import ProjectCreate, ProjectUpdate, SiteUpdate


def valid_registration(**overrides: object) -> dict[str, object]:
    """Return valid registration data with optional overrides.

    Keeps each test focused on the one field it changes.
    """
    data: dict[str, object] = {
        "email": "  Site.Engineer@Example.COM ",
        "password": "strongpass123",
        "name": "  Asha Verma ",
        "organization_name": "Verma Builders",
    }
    data.update(overrides)
    return data


def test_registration_normalises_email_and_names() -> None:
    """Email is lowercased and trimmed, names are trimmed, language defaults to English."""
    request = RegisterRequest(**valid_registration())  # type: ignore[arg-type]
    assert request.email == "site.engineer@example.com"
    assert request.name == "Asha Verma"
    assert request.preferred_language == "en"


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "not-an-email"},
        {"email": "a@b"},
        {"password": "short1"},
        {"password": "onlyletterspassword"},
        {"password": "1234567890123"},
        {"password": "x1" * 70},
        {"name": "   "},
        {"preferred_language": "fr"},
        {"unexpected_field": "x"},
    ],
)
def test_bad_registration_is_rejected(overrides: dict[str, object]) -> None:
    """Weak passwords, bad emails, blank names, unsupported language and extras fail."""
    with pytest.raises(ValidationError):
        RegisterRequest(**valid_registration(**overrides))  # type: ignore[arg-type]


def test_hindi_language_is_accepted_and_login_normalises_email() -> None:
    """Hindi is a supported language and login emails normalise the same way."""
    assert RegisterRequest(**valid_registration(preferred_language="hi")).preferred_language == "hi"  # type: ignore[arg-type]
    assert LoginRequest(email=" A@B.CO ", password="x").email == "a@b.co"


def test_member_add_rejects_unknown_role() -> None:
    """Only the five defined roles are accepted."""
    assert MemberAddRequest(email="a@b.co", role="engineer").role == "engineer"  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        MemberAddRequest(email="a@b.co", role="admin")  # type: ignore[arg-type]


def test_project_money_is_exact_decimal() -> None:
    """Contract value parses to Decimal exactly, from text or integer."""
    assert ProjectCreate(name="Tower", contract_value="1250000.50").contract_value == Decimal(
        "1250000.50"
    )  # type: ignore[arg-type]
    assert ProjectCreate(name="Tower", contract_value=5000).contract_value == Decimal("5000")  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_value", ["-1", "10.123", "1" * 17 + ".00", "abc"])
def test_bad_contract_values_are_rejected(bad_value: str) -> None:
    """Negative, more than two decimals, too large and non numeric values fail."""
    with pytest.raises(ValidationError):
        ProjectCreate(name="Tower", contract_value=bad_value)  # type: ignore[arg-type]


def test_float_money_is_not_silently_rounded() -> None:
    """A float with float noise is rejected rather than rounded."""
    with pytest.raises(ValidationError):
        ProjectCreate(name="Tower", contract_value=0.1 + 0.2)  # type: ignore[arg-type]


def test_end_date_before_start_date_is_rejected() -> None:
    """Dates out of order fail on create and on update."""
    with pytest.raises(ValidationError):
        ProjectCreate(name="Tower", start_date="2026-05-01", end_date="2026-04-01")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ProjectUpdate(start_date="2026-05-01", end_date="2026-04-01")  # type: ignore[arg-type]


def test_updates_require_a_field_and_forbid_null_names() -> None:
    """An empty update, or setting a name to null, is rejected."""
    with pytest.raises(ValidationError):
        ProjectUpdate()
    with pytest.raises(ValidationError):
        ProjectUpdate(name=None)
    with pytest.raises(ValidationError):
        SiteUpdate()
    with pytest.raises(ValidationError):
        SiteUpdate(name=None)
    assert ProjectUpdate(client_name=None).model_fields_set == {"client_name"}


def make_audit_table(dialect_name: str) -> sqlite3.Connection:
    """Create an in-memory SQLite database with a minimal audit_logs table and triggers.

    Returns the open connection for the test to use.
    """
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE audit_logs (id TEXT PRIMARY KEY, action TEXT)")
    for statement in audit_trigger_statements(dialect_name):
        connection.execute(statement)
    return connection


def test_sqlite_audit_triggers_allow_insert_but_block_update_and_delete() -> None:
    """Inserts work, while update and delete are aborted by the database itself."""
    connection = make_audit_table("sqlite")
    connection.execute("INSERT INTO audit_logs VALUES ('1', 'project.created')")
    with pytest.raises(sqlite3.DatabaseError, match="append only"):
        connection.execute("UPDATE audit_logs SET action = 'x' WHERE id = '1'")
    with pytest.raises(sqlite3.DatabaseError, match="append only"):
        connection.execute("DELETE FROM audit_logs WHERE id = '1'")
    assert connection.execute("SELECT action FROM audit_logs").fetchall() == [("project.created",)]


def test_sqlite_audit_triggers_can_be_dropped_for_rollback() -> None:
    """The drop statements remove the triggers so a migration can roll back."""
    connection = make_audit_table("sqlite")
    connection.execute("INSERT INTO audit_logs VALUES ('1', 'a')")
    for statement in audit_trigger_drop_statements("sqlite"):
        connection.execute(statement)
    connection.execute("UPDATE audit_logs SET action = 'b' WHERE id = '1'")
    assert connection.execute("SELECT action FROM audit_logs").fetchone() == ("b",)


def test_trigger_dialects() -> None:
    """PostgreSQL statements exist, and unknown dialects are rejected."""
    assert len(audit_trigger_statements("postgresql")) == 3
    assert len(audit_trigger_drop_statements("postgresql")) == 3
    with pytest.raises(ValueError):
        audit_trigger_statements("mysql")
    with pytest.raises(ValueError):
        audit_trigger_drop_statements("mysql")
