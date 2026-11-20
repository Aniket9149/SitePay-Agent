#Owner::ANIKET::ANHOTRA = MR.Panda
"""Organisation and membership data formats."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.schemas.auth_schema import _normalise_email
from app.security.permissions import Role

CleanOrganizationName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
CountryPackName = Literal["india", "generic"]


class OrganizationCreate(BaseModel):
    """Data to create another organisation. The creator becomes its owner."""

    model_config = ConfigDict(extra="forbid")

    name: CleanOrganizationName
    country_pack: CountryPackName = "india"


class OrganizationUpdate(BaseModel):
    """Fields of an organisation that may be changed."""

    model_config = ConfigDict(extra="forbid")

    name: CleanOrganizationName


class OrganizationResponse(BaseModel):
    """An organisation as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    country_pack: str
    created_at: datetime


class MemberAddRequest(BaseModel):
    """Add an existing registered user to the organisation by email."""

    model_config = ConfigDict(extra="forbid")

    email: str
    role: Role

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Normalise the email so lookups match how emails are stored.

        Delegates to the shared helper.
        """
        return _normalise_email(email)


class MemberRoleChangeRequest(BaseModel):
    """Change the role of an existing member."""

    model_config = ConfigDict(extra="forbid")

    role: Role


class MemberResponse(BaseModel):
    """A member of an organisation, with their role."""

    membership_id: str
    user_id: str
    name: str
    email: str
    role: Role
