#Owner::ANIKET::ANHOTRA = MR.Panda
"""Create companies, add members and assign roles."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import (
    OrganizationAccess,
    get_current_user,
    get_database_session,
    require_permission,
)
from app.models.user_model import User
from app.schemas.auth_schema import OrganizationSummary
from app.schemas.organization_schema import (
    MemberAddRequest,
    MemberResponse,
    MemberRoleChangeRequest,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.security.permissions import Permission
from app.services import auth_service, organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationSummary])
def list_my_organizations(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_database_session),
) -> list[OrganizationSummary]:
    """List the organisations the signed in user belongs to, with their roles.

    Only the user's own memberships are shown.
    """
    return [
        OrganizationSummary(
            id=organization.id, name=organization.name,
            country_pack=organization.country_pack, role=membership.role,
        )
        for organization, membership in auth_service.list_user_organizations(session, user.id)
    ]


@router.post("", response_model=OrganizationResponse, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_database_session),
) -> OrganizationResponse:
    """Create another organisation. The signed in user becomes its owner.

    Useful for a person who works with more than one company.
    """
    organization = organization_service.create_organization(session, user, payload)
    session.commit()
    return OrganizationResponse.model_validate(organization)


@router.get("/{organization_id}", response_model=OrganizationResponse)
def read_organization(
    access: OrganizationAccess = Depends(require_permission(Permission.ORGANIZATION_READ)),
    session: Session = Depends(get_database_session),
) -> OrganizationResponse:
    """Return one organisation the user belongs to.

    Non-members receive "not found".
    """
    organization = organization_service.get_organization(session, access.organization_id)
    return OrganizationResponse.model_validate(organization)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    payload: OrganizationUpdate,
    access: OrganizationAccess = Depends(require_permission(Permission.ORGANIZATION_UPDATE)),
    session: Session = Depends(get_database_session),
) -> OrganizationResponse:
    """Rename the organisation. Owners only.

    The change is written to the audit log.
    """
    organization = organization_service.rename_organization(
        session, access.organization_id, access.user, payload.name
    )
    session.commit()
    return OrganizationResponse.model_validate(organization)


@router.get("/{organization_id}/members", response_model=list[MemberResponse])
def list_organization_members(
    access: OrganizationAccess = Depends(require_permission(Permission.MEMBER_READ)),
    session: Session = Depends(get_database_session),
) -> list[MemberResponse]:
    """List the members of the organisation with their roles.

    Managers, accounts staff and owners may read this list.
    """
    return organization_service.list_members(session, access.organization_id)


@router.post("/{organization_id}/members", response_model=MemberResponse, status_code=201)
def add_organization_member(
    payload: MemberAddRequest,
    access: OrganizationAccess = Depends(require_permission(Permission.MEMBER_MANAGE)),
    session: Session = Depends(get_database_session),
) -> MemberResponse:
    """Add an already registered user to the organisation. Owners only.

    Inviting people who have no account yet comes later.
    """
    member = organization_service.add_member(
        session, access.organization_id, access.user, payload.email, payload.role
    )
    session.commit()
    return member


@router.patch("/{organization_id}/members/{membership_id}", response_model=MemberResponse)
def change_organization_member_role(
    membership_id: str,
    payload: MemberRoleChangeRequest,
    access: OrganizationAccess = Depends(require_permission(Permission.MEMBER_MANAGE)),
    session: Session = Depends(get_database_session),
) -> MemberResponse:
    """Change a member's role. Owners only, and the last owner cannot be demoted.

    The change is written to the audit log.
    """
    member = organization_service.change_member_role(
        session, access.organization_id, access.user, membership_id, payload.role
    )
    session.commit()
    return member


@router.delete("/{organization_id}/members/{membership_id}", status_code=204)
def remove_organization_member(
    membership_id: str,
    access: OrganizationAccess = Depends(require_permission(Permission.MEMBER_MANAGE)),
    session: Session = Depends(get_database_session),
) -> Response:
    """Remove a member. Owners only, and the last owner cannot be removed.

    The removal is written to the audit log.
    """
    organization_service.remove_member(session, access.organization_id, access.user, membership_id)
    session.commit()
    return Response(status_code=204)
