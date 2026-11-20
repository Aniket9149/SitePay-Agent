#Owner::ANIKET::ANHOTRA = MR.Panda
"""Project and site data formats. Money is Decimal with at most two decimal places."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ProjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
ContractValue = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]
CountryPackName = Literal["india", "generic"]


def _check_date_order(start_date: date | None, end_date: date | None) -> None:
    """Raise ValueError when both dates exist and the end is before the start.

    Used by both the create and update formats.
    """
    if start_date is not None and end_date is not None and end_date < start_date:
        raise ValueError("End date cannot be before the start date.")


class ProjectCreate(BaseModel):
    """Data to create a project."""

    model_config = ConfigDict(extra="forbid")

    name: ProjectName
    client_name: ShortText | None = None
    contract_value: ContractValue | None = None
    country_pack: CountryPackName = "india"
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> ProjectCreate:
        """Check that the end date is not before the start date.

        Runs after every field has been parsed.
        """
        _check_date_order(self.start_date, self.end_date)
        return self


class ProjectUpdate(BaseModel):
    """Fields of a project that may be changed. Only sent fields are changed."""

    model_config = ConfigDict(extra="forbid")

    name: ProjectName | None = None
    client_name: ShortText | None = None
    contract_value: ContractValue | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_update(self) -> ProjectUpdate:
        """Require at least one field and a sensible date order.

        The name cannot be set to null because a project always has a name.
        """
        if not self.model_fields_set:
            raise ValueError("Send at least one field to change.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("A project name cannot be empty.")
        _check_date_order(self.start_date, self.end_date)
        return self


class ProjectResponse(BaseModel):
    """A project as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    client_name: str | None
    contract_value: Decimal | None
    country_pack: str
    start_date: date | None
    end_date: date | None
    created_at: datetime


class SiteCreate(BaseModel):
    """Data to create a site or block inside a project."""

    model_config = ConfigDict(extra="forbid")

    name: ShortText
    location_description: LongText | None = None


class SiteUpdate(BaseModel):
    """Fields of a site that may be changed. Only sent fields are changed."""

    model_config = ConfigDict(extra="forbid")

    name: ShortText | None = None
    location_description: LongText | None = None

    @model_validator(mode="after")
    def validate_update(self) -> SiteUpdate:
        """Require at least one field, and never a null name.

        A site always keeps a name.
        """
        if not self.model_fields_set:
            raise ValueError("Send at least one field to change.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("A site name cannot be empty.")
        return self


class SiteResponse(BaseModel):
    """A site as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    organization_id: str
    name: str
    location_description: str | None
    created_at: datetime
