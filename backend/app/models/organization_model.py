#Owner::ANIKET::ANHOTRA = MR.Panda
"""Organisations (companies) table. Every business record belongs to one organisation."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import IdentifiedTimestampedModel


class Organization(IdentifiedTimestampedModel):
    """A contractor company. The unit of tenant separation."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country_pack: Mapped[str] = mapped_column(String(20), nullable=False, default="india")
