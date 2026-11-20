#Owner::ANIKET::ANHOTRA = MR.Panda
"""Naming rules for audit actions, and which workstream owns each action namespace.

An action is "namespace.verb" in lowercase, for example "project.created". Each workstream
writes only actions in its own namespaces, so the audit trail shows clearly which part of
the product did what. Adding a namespace is a change to this shared file.
"""

from __future__ import annotations

import re

from app.contracts.entity_references import Workstream
from app.errors import DomainValidationError

ACTION_PATTERN = re.compile(r"^[a-z][a-z_]*\.[a-z][a-z_]*$")
MAXIMUM_ACTION_LENGTH = 80

NAMESPACE_OWNER: dict[str, Workstream] = {
    "user": Workstream.ARCHITECT,
    "organization": Workstream.ARCHITECT,
    "membership": Workstream.ARCHITECT,
    "project": Workstream.ARCHITECT,
    "site": Workstream.ARCHITECT,
    "review": Workstream.ARCHITECT,
    "evidence": Workstream.EVIDENCE,
    "work_package": Workstream.QUANTUM,
    "activity": Workstream.QUANTUM,
    "measurement": Workstream.QUANTUM,
    "contract": Workstream.CONTRACT,
    "variation": Workstream.CONTRACT,
    "calculation": Workstream.LEDGER,
    "claim": Workstream.LEDGER,
}


def namespace_of(action: str) -> str:
    """Return the part of the action before the dot.

    Does not validate, use ensure_valid_audit_action for that.
    """
    return action.partition(".")[0]


def ensure_valid_audit_action(action: str) -> None:
    """Raise DomainValidationError unless the action is well formed and its namespace is known.

    Called before every audit record is written, so typos cannot enter the permanent log.
    """
    if len(action) > MAXIMUM_ACTION_LENGTH or ACTION_PATTERN.match(action) is None:
        raise DomainValidationError(f"Audit action is not in namespace.verb form: {action!r}")
    if namespace_of(action) not in NAMESPACE_OWNER:
        raise DomainValidationError(f"Audit action uses an unregistered namespace: {action!r}")


def action_owner(action: str) -> Workstream:
    """Return the workstream that owns the action's namespace.

    Raises DomainValidationError for an invalid action.
    """
    ensure_valid_audit_action(action)
    return NAMESPACE_OWNER[namespace_of(action)]
