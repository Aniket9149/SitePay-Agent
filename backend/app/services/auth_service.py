#Owner::ANIKET::ANHOTRA = MR.Panda
"""Registration, login, token refresh with rotation, and logout.

Refresh tokens are single use. Using an old one again is treated as theft and revokes
every token of that user. Passwords are checked in constant time, and unknown emails
cost the same time as known ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import flush_or_raise_conflict
from app.errors import AuthenticationError, ConflictError
from app.models.base_model import current_utc_time
from app.models.membership_model import Membership
from app.models.organization_model import Organization
from app.models.refresh_token_model import RefreshToken
from app.models.user_model import User
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenPair
from app.security import password_hasher
from app.security.permissions import Role
from app.security.token_service import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_token,
    decode_token,
)
from app.services.audit_service import record_audit_event

GENERIC_LOGIN_FAILURE = "Incorrect email or password."


@dataclass(frozen=True)
class RegistrationResult:
    """Everything created by a successful registration."""

    user: User
    organization: Organization
    membership: Membership
    tokens: TokenPair


def issue_token_pair(session: Session, user: User, settings: Settings) -> TokenPair:
    """Create an access token and a new, stored refresh token for the user.

    The refresh token row lets the server revoke it later.
    """
    now = current_utc_time()
    refresh_lifetime = timedelta(days=settings.refresh_token_lifetime_days)
    access_lifetime = timedelta(minutes=settings.access_token_lifetime_minutes)
    refresh_token = create_token(
        user_id=user.id,
        token_type=REFRESH_TOKEN_TYPE,
        secret_key=settings.secret_key,
        lifetime=refresh_lifetime,
        issued_at=now,
    )
    claims = decode_token(refresh_token, settings.secret_key, REFRESH_TOKEN_TYPE)
    session.add(
        RefreshToken(
            id=claims.token_id, user_id=user.id, created_at=now, expires_at=now + refresh_lifetime
        )
    )
    session.flush()
    access_token = create_token(
        user_id=user.id,
        token_type=ACCESS_TOKEN_TYPE,
        secret_key=settings.secret_key,
        lifetime=access_lifetime,
        issued_at=now,
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_in_seconds=int(access_lifetime.total_seconds()),
    )


def register_user_with_organization(
    session: Session, payload: RegisterRequest, settings: Settings
) -> RegistrationResult:
    """Create a user, their first organisation and an owner membership, with audit records.

    Raises ConflictError when the email is already registered.
    """
    existing_user = session.execute(
        select(User.id).where(User.email == payload.email)
    ).scalar_one_or_none()
    if existing_user is not None:
        raise ConflictError("An account with this email already exists.")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=password_hasher.hash_password(payload.password),
        preferred_language=payload.preferred_language,
    )
    organization = Organization(name=payload.organization_name)
    session.add_all([user, organization])
    flush_or_raise_conflict(session, "An account with this email already exists.")
    membership = Membership(user_id=user.id, organization_id=organization.id, role=Role.OWNER.value)
    session.add(membership)
    session.flush()
    record_audit_event(
        session, action="user.registered", target_type="user", target_id=user.id,
        actor_user_id=user.id, organization_id=organization.id,
        value_after={"email": user.email, "preferred_language": user.preferred_language},
    )
    record_audit_event(
        session, action="organization.created", target_type="organization",
        target_id=organization.id, actor_user_id=user.id, organization_id=organization.id,
        value_after={"name": organization.name, "country_pack": organization.country_pack},
    )
    record_audit_event(
        session, action="membership.created", target_type="membership", target_id=membership.id,
        actor_user_id=user.id, organization_id=organization.id,
        value_after={"user_id": user.id, "role": membership.role},
    )
    tokens = issue_token_pair(session, user, settings)
    return RegistrationResult(user, organization, membership, tokens)


def authenticate_user(session: Session, email: str, password: str) -> User:
    """Check the email and password and return the active user.

    Raises the same generic AuthenticationError for every kind of failure.
    """
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        password_hasher.verify_against_dummy_hash(password)
        raise AuthenticationError(GENERIC_LOGIN_FAILURE)
    if not password_hasher.verify_password(password, user.password_hash) or not user.is_active:
        raise AuthenticationError(GENERIC_LOGIN_FAILURE)
    if password_hasher.password_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash_password(password)
    return user


def login_user(session: Session, payload: LoginRequest, settings: Settings) -> tuple[User, TokenPair]:
    """Log a user in, issue tokens, and write a login audit record per organisation.

    Returns the user and the new token pair.
    """
    user = authenticate_user(session, payload.email, payload.password)
    organization_ids = session.execute(
        select(Membership.organization_id).where(Membership.user_id == user.id)
    ).scalars()
    for organization_id in organization_ids:
        record_audit_event(
            session, action="user.login", target_type="user", target_id=user.id,
            actor_user_id=user.id, organization_id=organization_id,
        )
    return user, issue_token_pair(session, user, settings)


def _revoke_all_user_tokens(session: Session, user_id: str) -> None:
    """Mark every unrevoked refresh token of the user as revoked now.

    Used when token theft is suspected.
    """
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=current_utc_time())
    )


def _load_valid_refresh_row(
    session: Session, refresh_token: str, settings: Settings, *, revoked_means_theft: bool = True
) -> RefreshToken:
    """Decode a refresh token and return its stored row if it is still usable.

    A reused (already revoked) token revokes all tokens and commits that before failing.
    """
    claims = decode_token(refresh_token, settings.secret_key, REFRESH_TOKEN_TYPE)
    row = session.get(RefreshToken, claims.token_id)
    if row is None or row.user_id != claims.user_id:
        raise AuthenticationError("The login token is invalid or has expired.")
    if row.revoked_at is not None:
        if revoked_means_theft:
            _revoke_all_user_tokens(session, row.user_id)
            session.commit()  # Must persist even though we raise, or the revocation is lost.
        raise AuthenticationError("The login token is invalid or has expired.")
    if row.expires_at <= current_utc_time():
        raise AuthenticationError("The login token is invalid or has expired.")
    return row


def refresh_session(session: Session, refresh_token: str, settings: Settings) -> TokenPair:
    """Exchange a valid refresh token for a new pair, revoking the old token.

    Each refresh token works exactly once.
    """
    row = _load_valid_refresh_row(session, refresh_token, settings)
    user = session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("The login token is invalid or has expired.")
    new_tokens = issue_token_pair(session, user, settings)
    new_claims = decode_token(new_tokens.refresh_token, settings.secret_key, REFRESH_TOKEN_TYPE)
    row.revoked_at = current_utc_time()
    row.replaced_by_token_id = new_claims.token_id
    session.flush()
    return new_tokens


def logout_user(session: Session, refresh_token: str, settings: Settings) -> None:
    """Revoke the given refresh token and write a logout audit record per organisation.

    Raises AuthenticationError if the token is invalid or already logged out.
    """
    row = _load_valid_refresh_row(session, refresh_token, settings, revoked_means_theft=False)
    row.revoked_at = current_utc_time()
    organization_ids = session.execute(
        select(Membership.organization_id).where(Membership.user_id == row.user_id)
    ).scalars()
    for organization_id in organization_ids:
        record_audit_event(
            session, action="user.logout", target_type="user", target_id=row.user_id,
            actor_user_id=row.user_id, organization_id=organization_id,
        )
    session.flush()


def get_active_user(session: Session, user_id: str) -> User:
    """Return the active user with this identifier, or raise AuthenticationError.

    Used to turn a verified access token into a user.
    """
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("The login token is invalid or has expired.")
    return user


def list_user_organizations(session: Session, user_id: str) -> list[tuple[Organization, Membership]]:
    """Return every organisation the user belongs to, with their membership.

    Ordered by organisation name for a stable display.
    """
    rows = session.execute(
        select(Organization, Membership)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user_id)
        .order_by(Organization.name)
    ).all()
    return [(organization, membership) for organization, membership in rows]
