#Owner::ANIKET::ANHOTRA = MR.Panda
"""Login, registration and token data formats."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MINIMUM_PASSWORD_LENGTH = 10
MAXIMUM_PASSWORD_LENGTH = 128

CleanName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
SupportedLanguage = Literal["en", "hi"]


def _normalise_email(email: str) -> str:
    """Trim and lowercase an email, and check its basic shape.

    Raises ValueError (shown as a 422 message) when it does not look like an email.
    """
    cleaned_email = email.strip().lower()
    if len(cleaned_email) > 254 or EMAIL_PATTERN.match(cleaned_email) is None:
        raise ValueError("Enter a valid email address.")
    return cleaned_email


class RegisterRequest(BaseModel):
    """Data needed to create a new account and its first organisation."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=MINIMUM_PASSWORD_LENGTH, max_length=MAXIMUM_PASSWORD_LENGTH)
    name: CleanName
    organization_name: CleanName
    preferred_language: SupportedLanguage = "en"

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Normalise the email so the same address is always stored one way.

        Delegates to the shared helper.
        """
        return _normalise_email(email)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        """Require at least one letter and one digit.

        Length limits are enforced by the field definition.
        """
        has_letter = any(character.isalpha() for character in password)
        has_digit = any(character.isdigit() for character in password)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one digit.")
        return password


class LoginRequest(BaseModel):
    """Email and password for logging in."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=1, max_length=MAXIMUM_PASSWORD_LENGTH)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Normalise the email the same way registration does.

        Delegates to the shared helper.
        """
        return _normalise_email(email)


class RefreshRequest(BaseModel):
    """A refresh token, sent to get a new token pair or to log out."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=4096)


class TokenPair(BaseModel):
    """The access and refresh tokens returned after login or refresh."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_token_expires_in_seconds: int


class UserResponse(BaseModel):
    """Public details of a user. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    preferred_language: str


class OrganizationSummary(BaseModel):
    """An organisation as seen by one of its members, with that member's role."""

    id: str
    name: str
    country_pack: str
    role: str


class RegistrationResponse(BaseModel):
    """Returned after registration: the user, their organisation and tokens."""

    user: UserResponse
    organization: OrganizationSummary
    tokens: TokenPair


class CurrentUserResponse(BaseModel):
    """Returned by the "who am I" route."""

    user: UserResponse
    organizations: list[OrganizationSummary]
    server_time: datetime
