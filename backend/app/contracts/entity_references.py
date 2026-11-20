#Owner::ANIKET::ANHOTRA = MR.Panda
"""Typed references between records, and which workstream owns each kind of record.

A reference is a logical pointer (kind plus identifier), not a database foreign key.
Workstreams store references to each other's records and ask the owner for the details,
so no workstream reaches into another's tables. Identifiers are UUID text everywhere.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

from app.errors import DomainValidationError


class Workstream(StrEnum):
    """The six parallel workstreams that build one product."""

    ARCHITECT = "SP-01"
    EVIDENCE = "SP-02"
    QUANTUM = "SP-03"
    CONTRACT = "SP-04"
    LEDGER = "SP-05"
    SENTINEL = "SP-06"


class EntityKind(StrEnum):
    """Every kind of record that another workstream may point at."""

    USER = "user"
    ORGANIZATION = "organization"
    MEMBERSHIP = "membership"
    PROJECT = "project"
    SITE = "site"
    AUDIT_ENTRY = "audit_entry"
    EVIDENCE_ITEM = "evidence_item"
    EVIDENCE_LINK = "evidence_link"
    WORK_PACKAGE = "work_package"
    ACTIVITY = "activity"
    MEASUREMENT = "measurement"
    CONTRACT = "contract"
    CONTRACT_CLAUSE = "contract_clause"
    VARIATION = "variation"
    CALCULATION = "calculation"
    PAYMENT_CLAIM = "payment_claim"
    CLAIM_LINE = "claim_line"


ENTITY_OWNER: dict[EntityKind, Workstream] = {
    EntityKind.USER: Workstream.ARCHITECT,
    EntityKind.ORGANIZATION: Workstream.ARCHITECT,
    EntityKind.MEMBERSHIP: Workstream.ARCHITECT,
    EntityKind.PROJECT: Workstream.ARCHITECT,
    EntityKind.SITE: Workstream.ARCHITECT,
    EntityKind.AUDIT_ENTRY: Workstream.ARCHITECT,
    EntityKind.EVIDENCE_ITEM: Workstream.EVIDENCE,
    EntityKind.EVIDENCE_LINK: Workstream.EVIDENCE,
    EntityKind.WORK_PACKAGE: Workstream.QUANTUM,
    EntityKind.ACTIVITY: Workstream.QUANTUM,
    EntityKind.MEASUREMENT: Workstream.QUANTUM,
    EntityKind.CONTRACT: Workstream.CONTRACT,
    EntityKind.CONTRACT_CLAUSE: Workstream.CONTRACT,
    EntityKind.VARIATION: Workstream.CONTRACT,
    EntityKind.CALCULATION: Workstream.LEDGER,
    EntityKind.PAYMENT_CLAIM: Workstream.LEDGER,
    EntityKind.CLAIM_LINE: Workstream.LEDGER,
}

REFERENCE_SEPARATOR = ":"


def normalise_identifier(identifier: str) -> str:
    """Validate that the text is a UUID and return it in lowercase canonical form.

    Raises DomainValidationError for anything else, so guessable ids never get in.
    """
    try:
        return str(uuid.UUID(str(identifier)))
    except (ValueError, AttributeError, TypeError) as error:
        raise DomainValidationError("An identifier must be a valid UUID.") from error


def owner_of(kind: EntityKind) -> Workstream:
    """Return the workstream that owns records of this kind.

    Only the owner may create, change or delete such records.
    """
    return ENTITY_OWNER[kind]


@dataclass(frozen=True)
class EntityReference:
    """An immutable pointer to one record, by kind and identifier."""

    kind: EntityKind
    entity_id: str

    def __post_init__(self) -> None:
        """Check the kind and normalise the identifier when the reference is created.

        Raises DomainValidationError for an unknown kind or a non-UUID identifier.
        """
        try:
            resolved_kind = EntityKind(self.kind)
        except ValueError as error:
            raise DomainValidationError(f"Unknown record kind: {self.kind}") from error
        object.__setattr__(self, "kind", resolved_kind)
        object.__setattr__(self, "entity_id", normalise_identifier(self.entity_id))

    @property
    def owner(self) -> Workstream:
        """The workstream that owns the referenced record.

        Ask this workstream's service for the record's details.
        """
        return owner_of(self.kind)

    def to_text(self) -> str:
        """Return the reference as text such as "project:3f2a...".

        This is the form stored in links and shown in logs.
        """
        return f"{self.kind.value}{REFERENCE_SEPARATOR}{self.entity_id}"

    @classmethod
    def from_text(cls, reference_text: str) -> EntityReference:
        """Parse text produced by to_text.

        Raises DomainValidationError when the text is not in kind:uuid form.
        """
        kind_text, separator, identifier = str(reference_text).partition(REFERENCE_SEPARATOR)
        if separator == "" or kind_text == "" or identifier == "":
            raise DomainValidationError("A reference must look like kind:identifier.")
        return cls(kind=kind_text, entity_id=identifier)  # type: ignore[arg-type]
