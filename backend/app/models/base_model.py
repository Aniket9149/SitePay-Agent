#Owner::ANIKET::ANHOTRA = MR.Panda
"""Common building blocks for every table: base class, identifiers and UTC timestamps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, String
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

# Predictable constraint names make migrations and rollbacks reliable.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UtcDateTime(TypeDecorator[datetime]):
    """A timestamp column that always stores and returns timezone aware UTC.

    SQLite drops timezones, so this type restores UTC on read. Naive input is refused.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Convert an aware time to UTC before saving, and refuse naive times.

        A naive time is ambiguous, so it is a programming error.
        """
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed, use timezone aware UTC.")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Return the stored time as timezone aware UTC.

        Databases that return naive times are assumed to hold UTC.
        """
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def generate_identifier() -> str:
    """Create a new random identifier as text.

    UUIDs are used so identifiers cannot be guessed or counted.
    """
    return str(uuid.uuid4())


def current_utc_time() -> datetime:
    """Return the current time as timezone aware UTC.

    Every created and updated column uses this one function.
    """
    return datetime.now(UTC)


class IdentifiedTimestampedModel(Base):
    """Abstract base with the common columns: identifier, created time, updated time."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_identifier)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=current_utc_time
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=current_utc_time, onupdate=current_utc_time
    )

    def __repr__(self) -> str:
        """Short text for logs and debugging that never includes personal data.

        Shows only the class name and identifier.
        """
        return f"<{type(self).__name__} {self.id}>"
