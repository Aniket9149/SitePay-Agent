#Owner::ANIKET::ANHOTRA = MR.Panda
"""Audit log table: a permanent, append only, hash chained record of every action."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, UniqueConstraint, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from app.errors import AuditLogImmutableError
from app.models.base_model import Base, UtcDateTime, current_utc_time, generate_identifier


class AuditLogEntry(Base):
    """One audit record: who did what, to which record, when, and why.

    Rows are chained by hash per chain scope (the organisation, or "platform").
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        UniqueConstraint("chain_scope", "chain_position", name="uq_audit_logs_chain_position"),
        Index("ix_audit_logs_organization_id", "organization_id"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_identifier)
    chain_scope: Mapped[str] = mapped_column(String(36), nullable=False)
    chain_position: Mapped[int] = mapped_column(Integer, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    value_before: Mapped[Any] = mapped_column(JSON(none_as_null=True), nullable=True)
    value_after: Mapped[Any] = mapped_column(JSON(none_as_null=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=current_utc_time
    )
    previous_entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)


@event.listens_for(AuditLogEntry, "before_update")
def block_audit_entry_update(
    mapper: Mapper[Any], connection: Connection, target: AuditLogEntry
) -> None:
    """Refuse any attempt to modify an audit entry through the ORM.

    The database triggers block it again at a lower level.
    """
    raise AuditLogImmutableError("Audit log entries cannot be changed.")


@event.listens_for(AuditLogEntry, "before_delete")
def block_audit_entry_delete(
    mapper: Mapper[Any], connection: Connection, target: AuditLogEntry
) -> None:
    """Refuse any attempt to delete an audit entry through the ORM.

    The database triggers block it again at a lower level.
    """
    raise AuditLogImmutableError("Audit log entries cannot be deleted.")
