#Owner::ANIKET::ANHOTRA = MR.Panda
"""Sites table: sites or blocks inside a project."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import IdentifiedTimestampedModel


class Site(IdentifiedTimestampedModel):
    """A site, block or area of a project. Carries the organisation for tenant filtering."""

    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_sites_project_name"),
        Index("ix_sites_organization_id", "organization_id"),
        Index("ix_sites_project_id", "project_id"),
    )

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
