#Owner::ANIKET::ANHOTRA = MR.Panda
"""Shared helpers for routes: settings, database session, current user and access checks."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AuthenticationError, NotFoundError, PermissionDeniedError
from app.feature_flags import FeatureFlags
from app.models.membership_model import Membership
from app.models.user_model import User
from app.security.client_address import extract_client_address
from app.security.login_throttle import LoginThrottle, RegistrationThrottle
from app.security.permissions import Permission, Role, role_has_permission
from app.security.token_service import ACCESS_TOKEN_TYPE, decode_token
from app.services.auth_service import get_active_user

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class OrganizationAccess:
    """The signed in user and their membership in one organisation."""

    user: User
    membership: Membership

    @property
    def organization_id(self) -> str:
        """The identifier of the organisation this access applies to.

        Convenience for routes and services.
        """
        return self.membership.organization_id

    @property
    def role(self) -> Role:
        """The user's role in this organisation.

        Parsed from the stored text.
        """
        return Role(self.membership.role)


def get_application_settings(request: Request) -> Settings:
    """Return the settings stored on the running application.

    Tests replace them by building the app with their own settings.
    """
    settings: Settings = request.app.state.settings
    return settings


def get_feature_flags(request: Request) -> FeatureFlags:
    """Return the feature flags stored on the running application.

    Routes use this to switch optional features on and off.
    """
    flags: FeatureFlags = request.app.state.feature_flags
    return flags


def get_login_throttle(request: Request) -> LoginThrottle:
    """Return the login throttle stored on the running application.

    One throttle is shared by all requests handled by this server process.
    """
    throttle: LoginThrottle = request.app.state.login_throttle
    return throttle


def get_registration_throttle(request: Request) -> RegistrationThrottle:
    """Return the registration throttle stored on the running application.

    One throttle is shared by all requests handled by this server process.
    """
    throttle: RegistrationThrottle = request.app.state.registration_throttle
    return throttle


def get_client_address(
    request: Request, settings: Settings = Depends(get_application_settings)
) -> str:
    """Return the address attempts are counted against for this request.

    Forwarded headers are believed only when trusted proxies are configured.
    """
    peer_host = request.client.host if request.client else None
    return extract_client_address(
        peer_host, request.headers.get("x-forwarded-for"), settings.trusted_proxy_count
    )


def get_database_session(request: Request) -> Iterator[Session]:
    """Open a database session for one request and always close it.

    Rolls back on any error. Routes commit explicitly when their work is complete.
    """
    session: Session = request.app.state.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_database_session),
    settings: Settings = Depends(get_application_settings),
) -> User:
    """Turn the bearer access token into the active user, or raise AuthenticationError.

    Refresh tokens are not accepted here.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Log in to continue.")
    claims = decode_token(credentials.credentials, settings.secret_key, ACCESS_TOKEN_TYPE)
    return get_active_user(session, claims.user_id)


def get_organization_access(
    organization_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_database_session),
) -> OrganizationAccess:
    """Confirm the user belongs to the organisation named in the path.

    Non-members get "not found", so the existence of other companies is not revealed.
    """
    membership = session.execute(
        select(Membership).where(
            Membership.user_id == user.id, Membership.organization_id == organization_id
        )
    ).scalar_one_or_none()
    if membership is None:
        raise NotFoundError("Organization not found.")
    return OrganizationAccess(user=user, membership=membership)


def require_permission(permission: Permission) -> Callable[..., OrganizationAccess]:
    """Build a route dependency that demands a permission in the path's organisation.

    The result raises PermissionDeniedError when the user's role lacks the permission.
    """

    def check_permission(
        access: OrganizationAccess = Depends(get_organization_access),
    ) -> OrganizationAccess:
        """Allow the request only if the user's role includes the permission.

        Returns the access object for the route to use.
        """
        if not role_has_permission(access.membership.role, permission):
            raise PermissionDeniedError("Your role does not allow this action.")
        return access

    return check_permission
