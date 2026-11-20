#Owner::ANIKET::ANHOTRA = MR.Panda
"""Writes audit records and checks the audit hash chain.

Every record says who did what to which record, when and why. Records are chained by
hash so tampering is detectable. See security/audit_hash.py for the hashing.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.contracts.audit_actions import ensure_valid_audit_action
from app.errors import ConflictError
from app.models.audit_log_model import AuditLogEntry
from app.models.base_model import current_utc_time
from app.security.audit_hash import (
    GENESIS_HASH,
    canonical_timestamp,
    compute_entry_hash,
    find_first_broken_position,
    make_json_safe,
)

PLATFORM_CHAIN_SCOPE = "platform"
MAXIMUM_CHAIN_WRITE_ATTEMPTS = 3


def _build_entry(
    session: Session,
    *,
    chain_scope: str,
    organization_id: str | None,
    actor_user_id: str | None,
    action: str,
    target_type: str,
    target_id: str | None,
    value_before: Any,
    value_after: Any,
    reason: str | None,
) -> AuditLogEntry:
    """Create the next chained entry for a scope, not yet saved.

    Reads the latest entry to get the previous hash and the next position.
    """
    latest_entry = session.execute(
        select(AuditLogEntry)
        .where(AuditLogEntry.chain_scope == chain_scope)
        .order_by(AuditLogEntry.chain_position.desc())
        .limit(1)
    ).scalar_one_or_none()
    previous_hash = latest_entry.entry_hash if latest_entry else GENESIS_HASH
    created_at = current_utc_time()
    fields: dict[str, Any] = {
        "chain_scope": chain_scope,
        "chain_position": latest_entry.chain_position + 1 if latest_entry else 1,
        "organization_id": organization_id,
        "actor_user_id": actor_user_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "value_before": make_json_safe(value_before),
        "value_after": make_json_safe(value_after),
        "reason": reason,
        "created_at": canonical_timestamp(created_at),
    }
    return AuditLogEntry(
        **{**fields, "created_at": created_at},
        previous_entry_hash=previous_hash,
        entry_hash=compute_entry_hash(previous_hash, fields),
    )


def record_audit_event(
    session: Session,
    *,
    action: str,
    target_type: str,
    target_id: str | None = None,
    actor_user_id: str | None = None,
    organization_id: str | None = None,
    value_before: Any = None,
    value_after: Any = None,
    reason: str | None = None,
) -> AuditLogEntry:
    """Append one audit entry to the chain of the organisation, or the platform chain.

    Retries when two writers race for the same position, then raises ConflictError.
    """
    ensure_valid_audit_action(action)
    chain_scope = organization_id or PLATFORM_CHAIN_SCOPE
    for attempt_number in range(1, MAXIMUM_CHAIN_WRITE_ATTEMPTS + 1):
        entry = _build_entry(
            session,
            chain_scope=chain_scope,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            value_before=value_before,
            value_after=value_after,
            reason=reason,
        )
        try:
            with session.begin_nested():
                session.add(entry)
                session.flush()
            return entry
        except IntegrityError:
            if attempt_number == MAXIMUM_CHAIN_WRITE_ATTEMPTS:
                raise ConflictError("The audit log is busy, please try again.") from None
    raise ConflictError("The audit log is busy, please try again.")


def find_broken_audit_position(session: Session, chain_scope: str) -> int | None:
    """Check one audit chain and return the first broken position, or None if intact.

    Used by tests, the security review and a future scheduled integrity check.
    """
    entries = session.execute(
        select(AuditLogEntry)
        .where(AuditLogEntry.chain_scope == chain_scope)
        .order_by(AuditLogEntry.chain_position)
    ).scalars()
    return find_first_broken_position(
        {
            "chain_scope": entry.chain_scope,
            "chain_position": entry.chain_position,
            "organization_id": entry.organization_id,
            "actor_user_id": entry.actor_user_id,
            "action": entry.action,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "value_before": entry.value_before,
            "value_after": entry.value_after,
            "reason": entry.reason,
            "created_at": canonical_timestamp(entry.created_at),
            "previous_entry_hash": entry.previous_entry_hash,
            "entry_hash": entry.entry_hash,
        }
        for entry in entries
    )


def list_audit_entries(
    session: Session, organization_id: str, limit: int = 50, offset: int = 0
) -> list[AuditLogEntry]:
    """Return an organisation's audit entries, newest first.

    Always filtered by organisation so one company never sees another's records.
    """
    return list(
        session.execute(
            select(AuditLogEntry)
            .where(AuditLogEntry.organization_id == organization_id)
            .order_by(AuditLogEntry.chain_position.desc())
            .limit(limit)
            .offset(offset)
        ).scalars()
    )
