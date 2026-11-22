#Owner::ANIKET::ANHOTRA = MR.Panda
"""Memberships table: which user belongs to which organisation with which role."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import IdentifiedTimestampedModel
from app.security.permissions import Role

ROLE_CHECK_SQL = "role IN (" + ", ".join(f"'{role.value}'" for role in Role) + ")"


class Membership(IdentifiedTimestampedModel):
    """Links one user to one organisation with exactly one role."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_organization"),
        CheckConstraint(ROLE_CHECK_SQL, name="role_is_known"),
        Index("ix_memberships_user_id", "user_id"),
        Index("ix_memberships_organization_id", "organization_id"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
