#Owner::ANIKET::ANHOTRA = MR.Panda
"""Projects table. Contract value is an exact decimal, never a floating point number."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import IdentifiedTimestampedModel


class Project(IdentifiedTimestampedModel):
    """A construction project belonging to one organisation."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_projects_organization_name"),
        CheckConstraint(
            "contract_value IS NULL OR contract_value >= 0",
            name="contract_value_not_negative",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="dates_in_order",
        ),
        Index("ix_projects_organization_id", "organization_id"),
    )

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contract_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    country_pack: Mapped[str] = mapped_column(String(20), nullable=False, default="india")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
