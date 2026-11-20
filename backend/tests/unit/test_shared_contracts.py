#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tests for the shared cross-workstream contracts, run for real without any framework."""

from __future__ import annotations

import ast
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.audit_actions import (
    NAMESPACE_OWNER,
    action_owner,
    ensure_valid_audit_action,
)
from app.contracts.entity_references import (
    ENTITY_OWNER,
    EntityKind,
    EntityReference,
    Workstream,
    owner_of,
)
from app.contracts.pagination import Page, PageRequest, build_page
from app.contracts.quantities_and_money import Money, Quantity, Unit
from app.contracts.review_states import (
    ALLOWED_TRANSITIONS,
    ActorType,
    ReviewState,
    can_role_decide,
    check_transition,
    is_final,
)
from app.errors import DomainValidationError, PermissionDeniedError
from app.security.permissions import Role

SERVICES_FOLDER = Path(__file__).resolve().parents[2] / "app" / "services"
SAMPLE_ID = str(uuid.uuid4())


def test_every_entity_kind_has_exactly_one_owner() -> None:
    """No record kind may be unowned, and the owners are real workstreams."""
    assert set(ENTITY_OWNER) == set(EntityKind)
    assert set(ENTITY_OWNER.values()) <= set(Workstream)


def test_core_records_belong_to_architect_and_domain_records_to_their_workstream() -> None:
    """Spot check the ownership map against the workstream definitions."""
    assert owner_of(EntityKind.PROJECT) is Workstream.ARCHITECT
    assert owner_of(EntityKind.EVIDENCE_ITEM) is Workstream.EVIDENCE
    assert owner_of(EntityKind.MEASUREMENT) is Workstream.QUANTUM
    assert owner_of(EntityKind.VARIATION) is Workstream.CONTRACT
    assert owner_of(EntityKind.PAYMENT_CLAIM) is Workstream.LEDGER


def test_reference_round_trip_and_normalisation() -> None:
    """A reference survives text conversion, and identifiers are lowercased."""
    reference = EntityReference(EntityKind.PROJECT, SAMPLE_ID.upper())
    assert reference.entity_id == SAMPLE_ID
    assert EntityReference.from_text(reference.to_text()) == reference
    assert reference.owner is Workstream.ARCHITECT


@pytest.mark.parametrize(
    "bad_text",
    ["", "project", "project:", ":" + SAMPLE_ID, "project:not-a-uuid", "planet:" + SAMPLE_ID, "project:1"],
)
def test_bad_reference_text_is_rejected(bad_text: str) -> None:
    """Malformed text, unknown kinds and guessable ids are all refused."""
    with pytest.raises(DomainValidationError):
        EntityReference.from_text(bad_text)


def test_reference_is_immutable_and_hashable() -> None:
    """References can be used as dictionary keys and cannot be changed."""
    reference = EntityReference(EntityKind.SITE, SAMPLE_ID)
    assert {reference: 1}[EntityReference(EntityKind.SITE, SAMPLE_ID)] == 1
    with pytest.raises(AttributeError):
        reference.entity_id = "x"  # type: ignore[misc]


def test_normal_review_path_is_allowed() -> None:
    """A person can take a record from draft through review to approved."""
    check_transition(ReviewState.DRAFT, ReviewState.IN_REVIEW, actor_type=ActorType.AGENT)
    check_transition(
        ReviewState.IN_REVIEW, ReviewState.APPROVED, actor_type=ActorType.HUMAN, actor_role=Role.ENGINEER
    )
    check_transition(ReviewState.APPROVED, ReviewState.SUPERSEDED, actor_type=ActorType.SYSTEM)


@pytest.mark.parametrize("actor_type", [ActorType.AGENT, ActorType.SYSTEM])
@pytest.mark.parametrize("target", [ReviewState.APPROVED, ReviewState.REJECTED])
def test_agents_and_system_can_never_decide(actor_type: ActorType, target: ReviewState) -> None:
    """Rule A2: only a person approves or rejects, even with a deciding role passed in."""
    with pytest.raises(PermissionDeniedError):
        check_transition(
            ReviewState.IN_REVIEW, target, actor_type=actor_type, actor_role=Role.OWNER, reason="x"
        )


@pytest.mark.parametrize("role", [Role.ACCOUNTS, Role.WORKER, "superuser", None])
def test_non_deciding_roles_cannot_approve(role: Role | str | None) -> None:
    """Workers, accounts staff, unknown roles and a missing role cannot approve."""
    with pytest.raises(PermissionDeniedError):
        check_transition(
            ReviewState.IN_REVIEW, ReviewState.APPROVED, actor_type=ActorType.HUMAN, actor_role=role
        )


def test_deciding_roles() -> None:
    """Owner, manager and engineer may decide by default."""
    assert [can_role_decide(role) for role in Role] == [True, True, True, False, False]
    assert can_role_decide("nonsense") is False


def test_rejection_needs_a_reason() -> None:
    """A rejection without a reason, or with only spaces, is refused."""
    for reason in (None, "", "   "):
        with pytest.raises(DomainValidationError):
            check_transition(
                ReviewState.IN_REVIEW, ReviewState.REJECTED,
                actor_type=ActorType.HUMAN, actor_role=Role.MANAGER, reason=reason,
            )
    check_transition(
        ReviewState.IN_REVIEW, ReviewState.REJECTED,
        actor_type=ActorType.HUMAN, actor_role=Role.MANAGER, reason="Measurement missing",
    )


def test_every_disallowed_transition_is_rejected() -> None:
    """Exhaustively: any move not in the table raises, including skipping review."""
    for current in ReviewState:
        for target in ReviewState:
            if target in ALLOWED_TRANSITIONS[current]:
                continue
            with pytest.raises(DomainValidationError):
                check_transition(
                    current, target, actor_type=ActorType.HUMAN, actor_role=Role.OWNER, reason="x"
                )


def test_draft_cannot_jump_to_approved_and_final_states() -> None:
    """Approval cannot skip review, and final states are identified."""
    with pytest.raises(DomainValidationError):
        check_transition(
            ReviewState.DRAFT, ReviewState.APPROVED, actor_type=ActorType.HUMAN, actor_role=Role.OWNER
        )
    assert is_final(ReviewState.APPROVED) and is_final(ReviewState.SUPERSEDED)
    assert not is_final(ReviewState.DRAFT) and not is_final(ReviewState.REJECTED)


@pytest.mark.parametrize("action", ["project.created", "claim.draft_created", "evidence.uploaded", "review.state_changed"])
def test_valid_audit_actions_pass(action: str) -> None:
    """Well formed actions in registered namespaces are accepted."""
    ensure_valid_audit_action(action)


@pytest.mark.parametrize(
    "action", ["", "project", "Project.created", "project.Created", "project.created.twice", "planet.visited", "a" * 90 + ".b", "project.", ".created"]
)
def test_invalid_audit_actions_fail(action: str) -> None:
    """Malformed actions and unregistered namespaces are refused."""
    with pytest.raises(DomainValidationError):
        ensure_valid_audit_action(action)


def test_action_owner_follows_namespace() -> None:
    """The owning workstream is found from the namespace."""
    assert action_owner("measurement.recorded") is Workstream.QUANTUM
    assert action_owner("claim.approved") is Workstream.LEDGER
    assert set(NAMESPACE_OWNER.values()) <= set(Workstream)


def test_every_action_used_by_the_services_is_valid() -> None:
    """Scan the service source for action="..." values and validate each one.

    Catches a typo that would otherwise only fail at run time inside a request.
    """
    found: list[str] = []
    for path in sorted(SERVICES_FOLDER.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.keyword) and node.arg == "action":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    found.append(node.value.value)
    assert len(found) >= 10
    for action in found:
        ensure_valid_audit_action(action)


def test_quantity_requires_unit_and_keeps_exact_amount() -> None:
    """Amounts stay exact and round trip through JSON text."""
    quantity = Quantity("12.50", "sqm")  # type: ignore[arg-type]
    assert quantity.amount == Decimal("12.50") and quantity.unit is Unit.SQUARE_METRE
    assert Quantity.from_json(quantity.to_json()) == quantity
    assert quantity.to_json() == {"amount": "12.50", "unit": "sqm"}


@pytest.mark.parametrize(
    "amount,unit",
    [(0.1, "sqm"), (True, "sqm"), ("abc", "sqm"), ("NaN", "sqm"), ("Infinity", "kg"), ("5", "feet"), ("5", ""), (None, "sqm")],
)
def test_bad_quantities_are_rejected(amount: object, unit: str) -> None:
    """Floats, booleans, non-numbers, non-finite values and unknown units fail."""
    with pytest.raises(DomainValidationError):
        Quantity(amount, unit)  # type: ignore[arg-type]


def test_quantity_from_json_needs_both_parts() -> None:
    """A missing amount or unit is an error."""
    with pytest.raises(DomainValidationError):
        Quantity.from_json({"amount": "1"})


def test_money_is_exact_and_validates_currency() -> None:
    """Large amounts stay exact and currency codes are checked."""
    money = Money("1250000.50", "INR")  # type: ignore[arg-type]
    assert money.amount == Decimal("1250000.50")
    assert Money.from_json(money.to_json()) == money
    assert Money(Decimal("0.1") + Decimal("0.2"), "INR").amount == Decimal("0.3")
    for bad_currency in ("inr", "RS", "INRX", ""):
        with pytest.raises(DomainValidationError):
            Money("1", bad_currency)
    with pytest.raises(DomainValidationError):
        Money(0.1 + 0.2, "INR")  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError):
        Money.from_json({"currency": "INR"})


def test_page_request_limits() -> None:
    """The limit must be 1 to 100 and the offset cannot be negative."""
    assert PageRequest().limit == 50 and PageRequest().fetch_limit == 51
    for bad in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        with pytest.raises(ValidationError):
            PageRequest(**bad)


def test_build_page_detects_more_rows_and_drops_the_extra() -> None:
    """With limit+1 rows there is a next page, and the extra row is dropped."""
    request = PageRequest(limit=3, offset=6)
    page = build_page(["a", "b", "c", "d"], request)
    assert page.items == ["a", "b", "c"] and page.has_more is True and page.next_offset == 9


def test_build_page_last_and_empty_pages() -> None:
    """Exactly limit rows, fewer rows and no rows all mean no further page."""
    request = PageRequest(limit=3)
    for rows in (["a", "b", "c"], ["a"], []):
        page = build_page(rows, request)
        assert page.items == rows and page.has_more is False and page.next_offset is None
    assert isinstance(build_page([1, 2], request), Page)
