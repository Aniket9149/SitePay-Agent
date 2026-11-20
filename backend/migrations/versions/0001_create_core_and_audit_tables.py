#Owner::ANIKET::ANHOTRA = MR.Panda
"""Create users, organisations, memberships, projects, sites, refresh tokens and audit log.

Also installs the append only triggers on the audit log. Constraint names follow the
naming convention in app/models/base_model.py so autogenerate shows no false changes.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.database_triggers import audit_trigger_drop_statements, audit_trigger_statements

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _timestamp_columns() -> list[sa.Column]:
    """Return fresh created_at and updated_at columns for a table.

    Both are timezone aware and required.
    """
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    """Create all Phase 1 tables, indexes, constraints and audit triggers."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        *_timestamp_columns(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("preferred_language", sa.String(5), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), nullable=False),
        *_timestamp_columns(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("country_pack", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_table(
        "memberships",
        sa.Column("id", sa.String(36), nullable=False),
        *_timestamp_columns(),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner', 'manager', 'engineer', 'accounts', 'worker')",
            name=op.f("ck_memberships_role_is_known"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_memberships_user_id_users"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_memberships_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memberships")),
        sa.UniqueConstraint(
            "user_id", "organization_id", name="uq_memberships_user_organization"
        ),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), nullable=False),
        *_timestamp_columns(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("client_name", sa.String(200), nullable=True),
        sa.Column("contract_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("country_pack", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.CheckConstraint(
            "contract_value IS NULL OR contract_value >= 0",
            name=op.f("ck_projects_contract_value_not_negative"),
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_projects_dates_in_order"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_projects_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name=op.f("fk_projects_created_by_user_id_users"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("organization_id", "name", name="uq_projects_organization_name"),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])
    op.create_table(
        "sites",
        sa.Column("id", sa.String(36), nullable=False),
        *_timestamp_columns(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("location_description", sa.String(1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_sites_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name=op.f("fk_sites_project_id_projects"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sites")),
        sa.UniqueConstraint("project_id", "name", name="uq_sites_project_name"),
    )
    op.create_index("ix_sites_organization_id", "sites", ["organization_id"])
    op.create_index("ix_sites_project_id", "sites", ["project_id"])
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("chain_scope", sa.String(36), nullable=False),
        sa.Column("chain_position", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(60), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=True),
        sa.Column("value_before", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("value_after", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_entry_hash", sa.String(64), nullable=False),
        sa.Column("entry_hash", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_audit_logs_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"],
            name=op.f("fk_audit_logs_actor_user_id_users"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
        sa.UniqueConstraint("chain_scope", "chain_position", name="uq_audit_logs_chain_position"),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_type", "target_id"])
    for statement in audit_trigger_statements(op.get_bind().dialect.name):
        op.execute(statement)


def downgrade() -> None:
    """Remove the audit triggers first, then drop every table in reverse order."""
    for statement in audit_trigger_drop_statements(op.get_bind().dialect.name):
        op.execute(statement)
    op.drop_table("audit_logs")
    op.drop_table("refresh_tokens")
    op.drop_table("sites")
    op.drop_table("projects")
    op.drop_table("memberships")
    op.drop_table("organizations")
    op.drop_table("users")
