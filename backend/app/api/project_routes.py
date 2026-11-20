#Owner::ANIKET::ANHOTRA = MR.Panda
"""Create, view and update projects inside an organisation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import OrganizationAccess, get_database_session, require_permission
from app.schemas.project_schema import ProjectCreate, ProjectResponse, ProjectUpdate
from app.security.permissions import Permission
from app.services import project_service

router = APIRouter(prefix="/organizations/{organization_id}/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreate,
    access: OrganizationAccess = Depends(require_permission(Permission.PROJECT_CREATE)),
    session: Session = Depends(get_database_session),
) -> ProjectResponse:
    """Create a project. Owners and managers only.

    Returns 409 when the organisation already has a project with the same name.
    """
    project = project_service.create_project(session, access.organization_id, access.user, payload)
    session.commit()
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    access: OrganizationAccess = Depends(require_permission(Permission.PROJECT_READ)),
    session: Session = Depends(get_database_session),
) -> list[ProjectResponse]:
    """List the organisation's projects, newest first.

    Paging keeps responses small on weak mobile connections.
    """
    projects = project_service.list_projects(session, access.organization_id, limit, offset)
    return [ProjectResponse.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def read_project(
    project_id: str,
    access: OrganizationAccess = Depends(require_permission(Permission.PROJECT_READ)),
    session: Session = Depends(get_database_session),
) -> ProjectResponse:
    """Return one project. A project of another organisation is "not found".

    Tenant separation is enforced in the query itself.
    """
    project = project_service.get_project(session, access.organization_id, project_id)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    access: OrganizationAccess = Depends(require_permission(Permission.PROJECT_UPDATE)),
    session: Session = Depends(get_database_session),
) -> ProjectResponse:
    """Change the sent fields of a project. Owners and managers only.

    Before and after values are written to the audit log.
    """
    project = project_service.update_project(
        session, access.organization_id, access.user, project_id, payload
    )
    session.commit()
    return ProjectResponse.model_validate(project)
