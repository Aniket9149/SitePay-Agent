#Owner::ANIKET::ANHOTRA = MR.Panda
"""Organisations and their members. Every change is audited and the last owner is protected."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import flush_or_raise_conflict
from app.errors import DomainValidationError, NotFoundError
from app.models.membership_model import Membership
from app.models.organization_model import Organization
from app.models.user_model import User
from app.schemas.organization_schema import MemberResponse, OrganizationCreate
from app.security.permissions import Role, would_leave_organization_without_owner
from app.services.audit_service import record_audit_event


def create_organization(session: Session, creator: User, payload: OrganizationCreate) -> Organization:
    """Create an organisation and make the creator its owner, with audit records.

    The creator can then add other members.
    """
    organization = Organization(name=payload.name, country_pack=payload.country_pack)
    session.add(organization)
    session.flush()
    membership = Membership(
        user_id=creator.id, organization_id=organization.id, role=Role.OWNER.value
    )
    session.add(membership)
    session.flush()
    record_audit_event(
        session, action="organization.created", target_type="organization",
        target_id=organization.id, actor_user_id=creator.id, organization_id=organization.id,
        value_after={"name": organization.name, "country_pack": organization.country_pack},
    )
    record_audit_event(
        session, action="membership.created", target_type="membership", target_id=membership.id,
        actor_user_id=creator.id, organization_id=organization.id,
        value_after={"user_id": creator.id, "role": membership.role},
    )
    return organization


def get_organization(session: Session, organization_id: str) -> Organization:
    """Return the organisation or raise NotFoundError.

    Access checks happen before this is called.
    """
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise NotFoundError("Organization not found.")
    return organization


def rename_organization(
    session: Session, organization_id: str, actor: User, new_name: str
) -> Organization:
    """Change the organisation name and write an audit record with before and after.

    Does nothing, and writes no audit record, when the name is unchanged.
    """
    organization = get_organization(session, organization_id)
    if organization.name != new_name:
        previous_name = organization.name
        organization.name = new_name
        session.flush()
        record_audit_event(
            session, action="organization.renamed", target_type="organization",
            target_id=organization.id, actor_user_id=actor.id, organization_id=organization.id,
            value_before={"name": previous_name}, value_after={"name": new_name},
        )
    return organization


def list_members(session: Session, organization_id: str) -> list[MemberResponse]:
    """Return all members of the organisation with their roles, ordered by name.

    Only this organisation's memberships are read.
    """
    rows = session.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == organization_id)
        .order_by(User.name)
    ).all()
    return [
        MemberResponse(
            membership_id=membership.id, user_id=user.id, name=user.name,
            email=user.email, role=Role(membership.role),
        )
        for membership, user in rows
    ]


def _current_roles(session: Session, organization_id: str) -> dict[str, Role]:
    """Map membership identifiers of the organisation to their roles.

    Feeds the last owner protection check.
    """
    rows = session.execute(
        select(Membership.id, Membership.role).where(Membership.organization_id == organization_id)
    ).all()
    return {membership_id: Role(role) for membership_id, role in rows}


def _get_membership(session: Session, organization_id: str, membership_id: str) -> Membership:
    """Return a membership of this organisation or raise NotFoundError.

    A membership of another organisation is reported as not found.
    """
    membership = session.execute(
        select(Membership).where(
            Membership.id == membership_id, Membership.organization_id == organization_id
        )
    ).scalar_one_or_none()
    if membership is None:
        raise NotFoundError("Member not found.")
    return membership


def add_member(
    session: Session, organization_id: str, actor: User, email: str, role: Role
) -> MemberResponse:
    """Add an existing registered user to the organisation with a role.

    Raises NotFoundError for an unknown email and ConflictError if already a member.
    """
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not user.is_active:
        raise NotFoundError("No registered user has this email address.")
    membership = Membership(user_id=user.id, organization_id=organization_id, role=role.value)
    session.add(membership)
    flush_or_raise_conflict(session, "This person is already a member of the organization.")
    record_audit_event(
        session, action="membership.created", target_type="membership", target_id=membership.id,
        actor_user_id=actor.id, organization_id=organization_id,
        value_after={"user_id": user.id, "role": role.value},
    )
    return MemberResponse(
        membership_id=membership.id, user_id=user.id, name=user.name, email=user.email, role=role
    )


def change_member_role(
    session: Session, organization_id: str, actor: User, membership_id: str, new_role: Role
) -> MemberResponse:
    """Change a member's role, protecting the last owner, with an audit record.

    Raises DomainValidationError if it would leave the organisation without an owner.
    """
    membership = _get_membership(session, organization_id, membership_id)
    roles = _current_roles(session, organization_id)
    if would_leave_organization_without_owner(roles, membership.id, new_role):
        raise DomainValidationError("An organization must keep at least one owner.")
    previous_role = membership.role
    if previous_role != new_role.value:
        membership.role = new_role.value
        session.flush()
        record_audit_event(
            session, action="membership.role_changed", target_type="membership",
            target_id=membership.id, actor_user_id=actor.id, organization_id=organization_id,
            value_before={"role": previous_role}, value_after={"role": new_role.value},
        )
    user = session.get(User, membership.user_id)
    if user is None:
        raise NotFoundError("Member not found.")
    return MemberResponse(
        membership_id=membership.id, user_id=user.id, name=user.name,
        email=user.email, role=new_role,
    )


def remove_member(session: Session, organization_id: str, actor: User, membership_id: str) -> None:
    """Remove a member from the organisation, protecting the last owner, with an audit record.

    Raises DomainValidationError if the member is the only owner.
    """
    membership = _get_membership(session, organization_id, membership_id)
    roles = _current_roles(session, organization_id)
    if would_leave_organization_without_owner(roles, membership.id, None):
        raise DomainValidationError("An organization must keep at least one owner.")
    removed_user_id, removed_role = membership.user_id, membership.role
    session.delete(membership)
    session.flush()
    record_audit_event(
        session, action="membership.removed", target_type="membership", target_id=membership_id,
        actor_user_id=actor.id, organization_id=organization_id,
        value_before={"user_id": removed_user_id, "role": removed_role},
    )
