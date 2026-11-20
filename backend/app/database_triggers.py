#Owner::ANIKET::ANHOTRA = MR.Panda
"""SQL that makes the audit_logs table append only inside the database itself.

Rule A7 says audit records cannot be edited. Application code also blocks updates, but
these triggers stop anyone using a direct database connection or a bulk statement.
The SQLite version is exercised by a test. The PostgreSQL version is not yet run.
"""

from __future__ import annotations

SQLITE_AUDIT_TRIGGER_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TRIGGER audit_logs_block_update BEFORE UPDATE ON audit_logs
    BEGIN SELECT RAISE(ABORT, 'audit_logs is append only'); END
    """,
    """
    CREATE TRIGGER audit_logs_block_delete BEFORE DELETE ON audit_logs
    BEGIN SELECT RAISE(ABORT, 'audit_logs is append only'); END
    """,
)
SQLITE_AUDIT_TRIGGER_DROP_STATEMENTS: tuple[str, ...] = (
    "DROP TRIGGER IF EXISTS audit_logs_block_update",
    "DROP TRIGGER IF EXISTS audit_logs_block_delete",
)

POSTGRESQL_AUDIT_TRIGGER_STATEMENTS: tuple[str, ...] = (
    """
    CREATE FUNCTION audit_logs_block_change() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_logs is append only';
    END;
    $$ LANGUAGE plpgsql
    """,
    """
    CREATE TRIGGER audit_logs_block_update_delete
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION audit_logs_block_change()
    """,
    """
    CREATE TRIGGER audit_logs_block_truncate
    BEFORE TRUNCATE ON audit_logs
    FOR EACH STATEMENT EXECUTE FUNCTION audit_logs_block_change()
    """,
)
POSTGRESQL_AUDIT_TRIGGER_DROP_STATEMENTS: tuple[str, ...] = (
    "DROP TRIGGER IF EXISTS audit_logs_block_truncate ON audit_logs",
    "DROP TRIGGER IF EXISTS audit_logs_block_update_delete ON audit_logs",
    "DROP FUNCTION IF EXISTS audit_logs_block_change()",
)


def audit_trigger_statements(dialect_name: str) -> tuple[str, ...]:
    """Return the statements that install the append only triggers for a database.

    Supports sqlite and postgresql, and raises ValueError for any other dialect.
    """
    if dialect_name == "sqlite":
        return SQLITE_AUDIT_TRIGGER_STATEMENTS
    if dialect_name == "postgresql":
        return POSTGRESQL_AUDIT_TRIGGER_STATEMENTS
    raise ValueError(f"No audit trigger defined for database dialect: {dialect_name}")


def audit_trigger_drop_statements(dialect_name: str) -> tuple[str, ...]:
    """Return the statements that remove the triggers again, for migration rollback.

    Supports sqlite and postgresql, and raises ValueError for any other dialect.
    """
    if dialect_name == "sqlite":
        return SQLITE_AUDIT_TRIGGER_DROP_STATEMENTS
    if dialect_name == "postgresql":
        return POSTGRESQL_AUDIT_TRIGGER_DROP_STATEMENTS
    raise ValueError(f"No audit trigger defined for database dialect: {dialect_name}")
