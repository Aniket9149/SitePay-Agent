#Owner::ANIKET::ANHOTRA = MR.Panda
"""Manage sites or blocks inside a project."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import OrganizationAccess, get_database_session, require_permission
from app.schemas.project_schema import SiteCreate, SiteResponse, SiteUpdate
from app.security.permissions import Permission
from app.services import project_service

router = APIRouter(
    prefix="/organizations/{organization_id}/projects/{project_id}/sites", tags=["sites"]
)


@router.post("", response_model=SiteResponse, status_code=201)
def create_site(
    project_id: str,
    payload: SiteCreate,
    access: OrganizationAccess = Depends(require_permission(Permission.SITE_MANAGE)),
    session: Session = Depends(get_database_session),
) -> SiteResponse:
    """Create a site in a project. Owners, managers and engineers.

    Returns 409 when the project already has a site with the same name.
    """
    site = project_service.create_site(
        session, access.organization_id, access.user, project_id, payload
    )
    session.commit()
    return SiteResponse.model_validate(site)


@router.get("", response_model=list[SiteResponse])
def list_sites(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    access: OrganizationAccess = Depends(require_permission(Permission.SITE_READ)),
    session: Session = Depends(get_database_session),
) -> list[SiteResponse]:
    """List the sites of a project, ordered by name.

    A project of another organisation is "not found".
    """
    sites = project_service.list_sites(session, access.organization_id, project_id, limit, offset)
    return [SiteResponse.model_validate(site) for site in sites]


@router.get("/{site_id}", response_model=SiteResponse)
def read_site(
    project_id: str,
    site_id: str,
    access: OrganizationAccess = Depends(require_permission(Permission.SITE_READ)),
    session: Session = Depends(get_database_session),
) -> SiteResponse:
    """Return one site of a project.

    Both the project and the organisation must match.
    """
    site = project_service.get_site(session, access.organization_id, project_id, site_id)
    return SiteResponse.model_validate(site)


@router.patch("/{site_id}", response_model=SiteResponse)
def update_site(
    project_id: str,
    site_id: str,
    payload: SiteUpdate,
    access: OrganizationAccess = Depends(require_permission(Permission.SITE_MANAGE)),
    session: Session = Depends(get_database_session),
) -> SiteResponse:
    """Change the sent fields of a site. Owners, managers and engineers.

    Before and after values are written to the audit log.
    """
    site = project_service.update_site(
        session, access.organization_id, access.user, project_id, site_id, payload
    )
    session.commit()
    return SiteResponse.model_validate(site)
