#Owner::ANIKET::ANHOTRA = MR.Panda
"""Runs the real Alembic migration on the database named by DATABASE_URL and checks the result.

Steps: upgrade, check tables, check the audit log refuses UPDATE and DELETE, downgrade,
check the tables are gone, upgrade again. Exits with status 1 and a message on any failure.
Works for SQLite and PostgreSQL. Run it from the project root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "organizations", "users", "memberships", "refresh_tokens", "projects", "sites", "audit_logs",
}


def alembic_config() -> object:
    """Build the Alembic configuration pointing at backend/migrations."""
    from alembic.config import Config

    config = Config(str(ROOT / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
    return config


def table_names(database_url: str) -> set[str]:
    """Return the names of all tables currently in the database."""
    from sqlalchemy import create_engine, inspect

    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def insert_audit_row(database_url: str) -> None:
    """Insert one valid audit row with raw SQL so the trigger checks have something to hit."""
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_logs (id, chain_scope, chain_position, action, target_type,"
                " created_at, previous_entry_hash, entry_hash) VALUES (:id, 'platform', 1,"
                " 'check.migration', 'check', CURRENT_TIMESTAMP, :zero, :one)"
            ),
            {"id": "00000000-0000-0000-0000-000000000001", "zero": "0" * 64, "one": "1" * 64},
        )
    engine.dispose()


def statement_is_refused(database_url: str, statement: str) -> bool:
    """Run a statement against the audit log and return True when the database rejects it."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import DBAPIError

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(statement))
    except DBAPIError:
        return True
    finally:
        engine.dispose()
    return False


def require(condition: bool, message: str) -> None:
    """Stop the script with a clear message when a check fails."""
    if not condition:
        print("FAIL: " + message)
        sys.exit(1)
    print("ok:   " + message)


def main() -> None:
    """Run every migration check in order."""
    from alembic import command

    database_url = os.environ["DATABASE_URL"]
    config = alembic_config()
    print("Database dialect: " + database_url.split(":", 1)[0])
    command.upgrade(config, "head")
    require(EXPECTED_TABLES <= table_names(database_url), "upgrade head created all tables")
    insert_audit_row(database_url)
    require(
        statement_is_refused(database_url, "UPDATE audit_logs SET action = 'tampered'"),
        "audit log refuses UPDATE",
    )
    require(
        statement_is_refused(database_url, "DELETE FROM audit_logs"), "audit log refuses DELETE"
    )
    command.downgrade(config, "base")
    require(
        not (EXPECTED_TABLES & table_names(database_url)), "downgrade base removed all tables"
    )
    command.upgrade(config, "head")
    require(EXPECTED_TABLES <= table_names(database_url), "second upgrade head works")
    print("All migration checks passed.")


if __name__ == "__main__":
    main()
