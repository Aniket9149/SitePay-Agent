#Owner::ANIKET::ANHOTRA = MR.Panda
"""Projects and sites. Every query is filtered by organisation (tenant separation)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import flush_or_raise_conflict
from app.errors import DomainValidationError, NotFoundError
from app.models.project_model import Project
from app.models.site_model import Site
from app.models.user_model import User
from app.schemas.project_schema import ProjectCreate, ProjectUpdate, SiteCreate, SiteUpdate
from app.services.audit_service import record_audit_event

PROJECT_AUDIT_FIELDS = (
    "name", "client_name", "contract_value", "country_pack", "start_date", "end_date",
)
SITE_AUDIT_FIELDS = ("name", "location_description")


def _snapshot(record: Project | Site, field_names: tuple[str, ...]) -> dict[str, Any]:
    """Copy the named fields of a record into a dict for the audit log.

    Values are made JSON safe by the audit service.
    """
    return {field_name: getattr(record, field_name) for field_name in field_names}


def create_project(
    session: Session, organization_id: str, actor: User, payload: ProjectCreate
) -> Project:
    """Create a project in the organisation and write an audit record.

    Raises ConflictError when the organisation already has a project with this name.
    """
    project = Project(
        organization_id=organization_id,
        created_by_user_id=actor.id,
        **payload.model_dump(),
    )
    session.add(project)
    flush_or_raise_conflict(session, "A project with this name already exists.")
    record_audit_event(
        session, action="project.created", target_type="project", target_id=project.id,
        actor_user_id=actor.id, organization_id=organization_id,
        value_after=_snapshot(project, PROJECT_AUDIT_FIELDS),
    )
    return project


def list_projects(
    session: Session, organization_id: str, limit: int = 50, offset: int = 0
) -> list[Project]:
    """Return the organisation's projects, newest first, with paging.

    Only this organisation's projects are ever returned.
    """
    return list(
        session.execute(
            select(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.created_at.desc(), Project.id)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


def get_project(session: Session, organization_id: str, project_id: str) -> Project:
    """Return one project of the organisation, or raise NotFoundError.

    A project of another organisation is reported as not found.
    """
    project = session.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == organization_id)
    ).scalar_one_or_none()
    if project is None:
        raise NotFoundError("Project not found.")
    return project


def update_project(
    session: Session, organization_id: str, actor: User, project_id: str, payload: ProjectUpdate
) -> Project:
    """Apply only the fields that were sent, then audit the before and after values.

    Raises DomainValidationError if the merged dates are out of order.
    """
    project = get_project(session, organization_id, project_id)
    before = _snapshot(project, PROJECT_AUDIT_FIELDS)
    for field_name in payload.model_fields_set:
        setattr(project, field_name, getattr(payload, field_name))
    if (
        project.start_date is not None
        and project.end_date is not None
        and project.end_date < project.start_date
    ):
        raise DomainValidationError("End date cannot be before the start date.")
    after = _snapshot(project, PROJECT_AUDIT_FIELDS)
    if before != after:
        flush_or_raise_conflict(session, "A project with this name already exists.")
        record_audit_event(
            session, action="project.updated", target_type="project", target_id=project.id,
            actor_user_id=actor.id, organization_id=organization_id,
            value_before={key: before[key] for key in after if before[key] != after[key]},
            value_after={key: after[key] for key in after if before[key] != after[key]},
        )
    return project


def create_site(
    session: Session, organization_id: str, actor: User, project_id: str, payload: SiteCreate
) -> Site:
    """Create a site inside a project of the organisation and write an audit record.

    Raises NotFoundError for a foreign project and ConflictError for a duplicate name.
    """
    project = get_project(session, organization_id, project_id)
    site = Site(organization_id=organization_id, project_id=project.id, **payload.model_dump())
    session.add(site)
    flush_or_raise_conflict(session, "A site with this name already exists in the project.")
    record_audit_event(
        session, action="site.created", target_type="site", target_id=site.id,
        actor_user_id=actor.id, organization_id=organization_id,
        value_after={"project_id": project.id, **_snapshot(site, SITE_AUDIT_FIELDS)},
    )
    return site


def list_sites(
    session: Session, organization_id: str, project_id: str, limit: int = 50, offset: int = 0
) -> list[Site]:
    """Return the sites of one project of the organisation, ordered by name.

    Raises NotFoundError when the project is not in this organisation.
    """
    project = get_project(session, organization_id, project_id)
    return list(
        session.execute(
            select(Site)
            .where(Site.project_id == project.id, Site.organization_id == organization_id)
            .order_by(Site.name)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


def get_site(session: Session, organization_id: str, project_id: str, site_id: str) -> Site:
    """Return one site of a project of the organisation, or raise NotFoundError.

    Both the project and the organisation must match.
    """
    site = session.execute(
        select(Site).where(
            Site.id == site_id,
            Site.project_id == project_id,
            Site.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if site is None:
        raise NotFoundError("Site not found.")
    return site


def update_site(
    session: Session,
    organization_id: str,
    actor: User,
    project_id: str,
    site_id: str,
    payload: SiteUpdate,
) -> Site:
    """Apply only the fields that were sent to a site, then audit the changes.

    Writes nothing when no value actually changed.
    """
    site = get_site(session, organization_id, project_id, site_id)
    before = _snapshot(site, SITE_AUDIT_FIELDS)
    for field_name in payload.model_fields_set:
        setattr(site, field_name, getattr(payload, field_name))
    after = _snapshot(site, SITE_AUDIT_FIELDS)
    if before != after:
        flush_or_raise_conflict(session, "A site with this name already exists in the project.")
        record_audit_event(
            session, action="site.updated", target_type="site", target_id=site.id,
            actor_user_id=actor.id, organization_id=organization_id,
            value_before={key: before[key] for key in after if before[key] != after[key]},
            value_after={key: after[key] for key in after if before[key] != after[key]},
        )
    return site
