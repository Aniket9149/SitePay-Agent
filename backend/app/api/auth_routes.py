#Owner::ANIKET::ANHOTRA = MR.Panda
"""Registration, login, token refresh, logout and "who am I".

Password reset needs email delivery, which arrives with the notification work, so it is
not offered yet. It is behind the password_reset feature flag in feature_flags.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies import (
    get_application_settings,
    get_client_address,
    get_current_user,
    get_database_session,
    get_login_throttle,
    get_registration_throttle,
)
from app.errors import AuthenticationError
from app.models.base_model import current_utc_time
from app.models.user_model import User
from app.schemas.auth_schema import (
    CurrentUserResponse,
    LoginRequest,
    OrganizationSummary,
    RefreshRequest,
    RegisterRequest,
    RegistrationResponse,
    TokenPair,
    UserResponse,
)
from app.security.login_throttle import LoginThrottle, RegistrationThrottle
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _summaries(session: Session, user_id: str) -> list[OrganizationSummary]:
    """List the user's organisations with their roles for responses.

    Ordered by organisation name.
    """
    return [
        OrganizationSummary(
            id=organization.id, name=organization.name,
            country_pack=organization.country_pack, role=membership.role,
        )
        for organization, membership in auth_service.list_user_organizations(session, user_id)
    ]


@router.post("/register", response_model=RegistrationResponse, status_code=201)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_database_session),
    settings: Settings = Depends(get_application_settings),
    throttle: RegistrationThrottle = Depends(get_registration_throttle),
    client_address: str = Depends(get_client_address),
) -> RegistrationResponse:
    """Create an account with its first organisation and return tokens.

    The new user becomes the organisation's owner. Each address may register only a few per hour.
    """
    throttle.register_attempt(client_address)
    result = auth_service.register_user_with_organization(session, payload, settings)
    session.commit()
    return RegistrationResponse(
        user=UserResponse.model_validate(result.user),
        organization=OrganizationSummary(
            id=result.organization.id, name=result.organization.name,
            country_pack=result.organization.country_pack, role=result.membership.role,
        ),
        tokens=result.tokens,
    )


@router.post("/login", response_model=TokenPair)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_database_session),
    settings: Settings = Depends(get_application_settings),
    throttle: LoginThrottle = Depends(get_login_throttle),
    client_address: str = Depends(get_client_address),
) -> TokenPair:
    """Check the email and password and return a token pair.

    Every failure returns the same generic message. Too many failures lock the login for a while.
    """
    throttle.ensure_allowed(payload.email, client_address)
    try:
        _user, tokens = auth_service.login_user(session, payload, settings)
    except AuthenticationError:
        throttle.register_failure(payload.email, client_address)
        raise
    throttle.register_success(payload.email, client_address)
    session.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair)
def refresh(
    payload: RefreshRequest,
    session: Session = Depends(get_database_session),
    settings: Settings = Depends(get_application_settings),
) -> TokenPair:
    """Exchange a refresh token for a new token pair. Each refresh token works once.

    Reusing an old token revokes all of the user's tokens.
    """
    tokens = auth_service.refresh_session(session, payload.refresh_token, settings)
    session.commit()
    return tokens


@router.post("/logout", status_code=204)
def logout(
    payload: RefreshRequest,
    session: Session = Depends(get_database_session),
    settings: Settings = Depends(get_application_settings),
) -> Response:
    """Revoke the refresh token so it cannot be used again.

    The short lived access token simply expires.
    """
    auth_service.logout_user(session, payload.refresh_token, settings)
    session.commit()
    return Response(status_code=204)


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_database_session),
) -> CurrentUserResponse:
    """Return the signed in user and the organisations they belong to.

    The frontend calls this after login to build its screens.
    """
    return CurrentUserResponse(
        user=UserResponse.model_validate(user),
        organizations=_summaries(session, user.id),
        server_time=current_utc_time(),
    )
