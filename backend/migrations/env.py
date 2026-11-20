#Owner::ANIKET::ANHOTRA = MR.Panda
"""Configuration for the Alembic migration tool.

The database url is read from the DATABASE_URL environment variable, never from a file.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models import Base

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


def read_database_url() -> str:
    """Return the database url from the environment, or stop with a clear message.

    Migrations must never run against a database chosen by accident.
    """
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url == "":
        raise RuntimeError("DATABASE_URL must be set to run migrations.")
    return database_url


def run_migrations_offline() -> None:
    """Write the migration SQL without connecting to the database.

    Useful for review before a production release.
    """
    context.configure(
        url=read_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply the migrations.

    SQLite runs in batch mode because it cannot alter tables in place.
    """
    configuration = alembic_config.get_section(alembic_config.config_ini_section, {})
    configuration["sqlalchemy.url"] = read_database_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
