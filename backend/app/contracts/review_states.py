#Owner::ANIKET::ANHOTRA = MR.Panda
"""The shared review and approval lifecycle, and who may decide.

Rule A2: no claim or report becomes final without a qualified person. An agent or the
system may draft and submit for review, never approve or reject. The roles allowed to
decide are a default. Who may approve in a small company is an open question in the
roadmap and is settled with the owner before the scope freeze.
"""

from __future__ import annotations

from enum import StrEnum

from app.errors import DomainValidationError, PermissionDeniedError
from app.security.permissions import Role


class ReviewState(StrEnum):
    """Where a draft record stands in the approval process."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ActorType(StrEnum):
    """Who is acting: a person, an AI agent or an automatic system step."""

    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


ALLOWED_TRANSITIONS: dict[ReviewState, frozenset[ReviewState]] = {
    ReviewState.DRAFT: frozenset({ReviewState.IN_REVIEW}),
    ReviewState.IN_REVIEW: frozenset(
        {ReviewState.APPROVED, ReviewState.REJECTED, ReviewState.DRAFT}
    ),
    ReviewState.REJECTED: frozenset({ReviewState.DRAFT}),
    ReviewState.APPROVED: frozenset({ReviewState.SUPERSEDED}),
    ReviewState.SUPERSEDED: frozenset(),
}
DECISION_STATES = frozenset({ReviewState.APPROVED, ReviewState.REJECTED})
DECIDING_ROLES = frozenset({Role.OWNER, Role.MANAGER, Role.ENGINEER})


def can_role_decide(role: Role | str) -> bool:
    """Return True when a person in this role may approve or reject.

    Unknown role text may not decide.
    """
    try:
        return Role(role) in DECIDING_ROLES
    except ValueError:
        return False


def check_transition(
    current_state: ReviewState,
    target_state: ReviewState,
    *,
    actor_type: ActorType,
    actor_role: Role | str | None = None,
    reason: str | None = None,
) -> None:
    """Raise an error unless this actor may move the record from the current to the target state.

    Approving or rejecting needs a person in a deciding role, and a rejection needs a reason.
    """
    if target_state not in ALLOWED_TRANSITIONS[current_state]:
        raise DomainValidationError(
            f"A record cannot move from {current_state.value} to {target_state.value}."
        )
    if target_state in DECISION_STATES:
        if actor_type is not ActorType.HUMAN:
            raise PermissionDeniedError("Only a person can approve or reject.")
        if actor_role is None or not can_role_decide(actor_role):
            raise PermissionDeniedError("Your role cannot approve or reject.")
    if target_state is ReviewState.REJECTED and (reason is None or reason.strip() == ""):
        raise DomainValidationError("A rejection needs a reason.")


def is_final(state: ReviewState) -> bool:
    """Return True when the state needs no more review work.

    Approved and superseded records are final, and rejected ones return to draft instead.
    """
    return state in (ReviewState.APPROVED, ReviewState.SUPERSEDED)
