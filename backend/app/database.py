#Owner::ANIKET::ANHOTRA = MR.Panda
"""Database connection and session setup."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool

from app.errors import ConflictError


def build_engine(database_url: str) -> Engine:
    """Create the engine for the given url, with safe settings per database.

    SQLite gets foreign key enforcement switched on, and in memory SQLite shares one connection.
    """
    if database_url.startswith("sqlite"):
        engine_options: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            engine_options["poolclass"] = StaticPool
        engine = create_engine(database_url, **engine_options)

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(
            dbapi_connection: DBAPIConnection, connection_record: ConnectionPoolEntry
        ) -> None:
            """Turn on foreign key checks, which SQLite leaves off by default.

            Runs once for every new database connection.
            """
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(database_url, pool_pre_ping=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the session factory bound to the engine.

    Sessions do not expire objects on commit, so responses can read them afterwards.
    """
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def flush_or_raise_conflict(session: Session, conflict_message: str) -> None:
    """Flush pending changes and turn a uniqueness clash into a ConflictError.

    The flush runs in a savepoint so the rest of the transaction stays usable.
    """
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as error:
        raise ConflictError(conflict_message) from error
