#Owner::ANIKET::ANHOTRA = MR.Panda
"""Role based access control: which role may do what inside an organisation.

The matrix below is a starting default. Who may approve claims and resolve conflicts
in a small company is an open question in the roadmap, so it is reviewed with the owner
before the scope freeze. Later phases add permissions here, never elsewhere.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from app.errors import DomainValidationError


class Role(StrEnum):
    """The five roles named in the roadmap."""

    OWNER = "owner"
    MANAGER = "manager"
    ENGINEER = "engineer"
    ACCOUNTS = "accounts"
    WORKER = "worker"


class Permission(StrEnum):
    """Actions that can be allowed or denied."""

    ORGANIZATION_READ = "organization:read"
    ORGANIZATION_UPDATE = "organization:update"
    MEMBER_READ = "member:read"
    MEMBER_MANAGE = "member:manage"
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    SITE_READ = "site:read"
    SITE_MANAGE = "site:manage"
    AUDIT_READ = "audit:read"


_READ_ONLY = frozenset(
    {Permission.ORGANIZATION_READ, Permission.PROJECT_READ, Permission.SITE_READ}
)

ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.MANAGER: _READ_ONLY
    | {
        Permission.MEMBER_READ,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_UPDATE,
        Permission.SITE_MANAGE,
        Permission.AUDIT_READ,
    },
    Role.ENGINEER: _READ_ONLY | {Permission.SITE_MANAGE},
    Role.ACCOUNTS: _READ_ONLY | {Permission.MEMBER_READ},
    Role.WORKER: _READ_ONLY,
}


def parse_role(role_text: str) -> Role:
    """Convert text such as "engineer" to a Role.

    Raises DomainValidationError for an unknown role name.
    """
    try:
        return Role(role_text)
    except ValueError as error:
        raise DomainValidationError(f"Unknown role: {role_text}") from error


def role_has_permission(role: Role | str, permission: Permission) -> bool:
    """Return True when the role is allowed the permission.

    Unknown role text is treated as having no permissions.
    """
    try:
        resolved_role = role if isinstance(role, Role) else Role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS[resolved_role]


def would_leave_organization_without_owner(
    member_roles: Mapping[str, Role | str], changed_member_id: str, new_role: Role | None
) -> bool:
    """Return True if the change would leave the organisation with no owner.

    Pass new_role=None to test removing the member. An organisation must keep one owner.
    """
    remaining_owner_count = 0
    for member_id, role in member_roles.items():
        effective_role = new_role if member_id == changed_member_id else role
        if member_id == changed_member_id and new_role is None:
            continue
        if effective_role == Role.OWNER:
            remaining_owner_count += 1
    return remaining_owner_count == 0
