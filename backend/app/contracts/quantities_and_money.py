#Owner::ANIKET::ANHOTRA = MR.Panda
"""Shared shapes for a quantity with a unit and an amount of money.

Rules C2 and F2: every quantity carries a unit, and money is an exact Decimal, never a
float. These are only value shapes with validation. Calculation, rounding and totals belong
to SP-05 Ledger (financial engine) and SP-03 Quantum, which must build on these shapes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from app.errors import DomainValidationError

CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


class Unit(StrEnum):
    """Units of measure named in the project rules."""

    SQUARE_METRE = "sqm"
    CUBIC_METRE = "cum"
    RUNNING_METRE = "rm"
    NUMBER = "nos"
    KILOGRAM = "kg"
    TONNE = "tonne"


def parse_decimal(value: object, field_label: str) -> Decimal:
    """Convert text, an integer or a Decimal to a finite Decimal.

    Floats are refused because they cannot hold exact amounts.
    """
    if isinstance(value, float) or isinstance(value, bool):
        raise DomainValidationError(f"{field_label} must be text or a Decimal, not a float.")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as error:
        raise DomainValidationError(f"{field_label} is not a valid number.") from error
    if not parsed.is_finite():
        raise DomainValidationError(f"{field_label} must be a finite number.")
    return parsed


@dataclass(frozen=True)
class Quantity:
    """An exact amount with a mandatory unit, for example 12.50 sqm."""

    amount: Decimal
    unit: Unit

    def __post_init__(self) -> None:
        """Validate and normalise the amount and unit when created.

        Raises DomainValidationError for a float, a non-number, or an unknown unit.
        """
        try:
            resolved_unit = Unit(self.unit)
        except ValueError as error:
            raise DomainValidationError(f"Unknown unit: {self.unit}") from error
        object.__setattr__(self, "unit", resolved_unit)
        object.__setattr__(self, "amount", parse_decimal(self.amount, "Quantity"))

    def to_json(self) -> dict[str, str]:
        """Return a JSON safe form that keeps the amount exact as text.

        Round trips through from_json.
        """
        return {"amount": str(self.amount), "unit": self.unit.value}

    @classmethod
    def from_json(cls, data: dict[str, str]) -> Quantity:
        """Build a Quantity from the to_json form.

        Raises DomainValidationError when a part is missing or invalid.
        """
        if "amount" not in data or "unit" not in data:
            raise DomainValidationError("A quantity needs both an amount and a unit.")
        return cls(amount=data["amount"], unit=data["unit"])  # type: ignore[arg-type]


@dataclass(frozen=True)
class Money:
    """An exact amount of money with a three letter currency code, for example INR."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        """Validate the amount and currency when created.

        Raises DomainValidationError for a float, a non-number or a bad currency code.
        """
        if CURRENCY_PATTERN.match(str(self.currency)) is None:
            raise DomainValidationError("Currency must be a three letter uppercase code.")
        object.__setattr__(self, "amount", parse_decimal(self.amount, "Money"))

    def to_json(self) -> dict[str, str]:
        """Return a JSON safe form that keeps the amount exact as text.

        Round trips through from_json.
        """
        return {"amount": str(self.amount), "currency": self.currency}

    @classmethod
    def from_json(cls, data: dict[str, str]) -> Money:
        """Build Money from the to_json form.

        Raises DomainValidationError when a part is missing or invalid.
        """
        if "amount" not in data or "currency" not in data:
            raise DomainValidationError("Money needs both an amount and a currency.")
        return cls(amount=data["amount"], currency=data["currency"])  # type: ignore[arg-type]
