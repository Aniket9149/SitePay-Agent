#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tamper evident hash chain for the audit log.

Each audit entry stores the hash of the entry before it. Changing or removing any
past entry breaks every later hash, so tampering is detectable. The database also
blocks updates and deletes (see database_triggers.py). This file is pure Python.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

GENESIS_HASH = "0" * 64
HASHED_FIELD_NAMES = (
    "chain_scope",
    "chain_position",
    "organization_id",
    "actor_user_id",
    "action",
    "target_type",
    "target_id",
    "value_before",
    "value_after",
    "reason",
    "created_at",
)


def canonical_timestamp(moment: datetime) -> str:
    """Format a time as UTC text with microseconds, the same way every time.

    A naive time is treated as UTC, because the database stores UTC.
    """
    utc_moment = moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
    return utc_moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def make_json_safe(value: Any) -> Any:  # noqa: ANN401 - arbitrary JSON in, JSON out
    """Convert a value into plain JSON types without losing exact amounts.

    Decimals become text, dates become ISO text and enums become their values.
    """
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return canonical_timestamp(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return make_json_safe(value.value)
    if isinstance(value, Mapping):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [make_json_safe(item) for item in value]
    return str(value)


def compute_entry_hash(previous_entry_hash: str, entry_fields: Mapping[str, Any]) -> str:
    """Hash one audit entry together with the hash of the entry before it.

    Fields are written as canonical JSON so the result never depends on key order.
    """
    selected_fields = {name: entry_fields.get(name) for name in HASHED_FIELD_NAMES}
    canonical_text = json.dumps(
        {"previous": previous_entry_hash, "entry": selected_fields},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


def find_first_broken_position(entries: Iterable[Mapping[str, Any]]) -> int | None:
    """Check a chain in order and return the first position that is wrong.

    Each entry needs its fields plus stored previous_entry_hash and entry_hash.
    Returns None when the whole chain is intact.
    """
    expected_previous_hash = GENESIS_HASH
    expected_position = 1
    for entry in entries:
        position = int(entry["chain_position"])
        if position != expected_position:
            return expected_position
        if entry["previous_entry_hash"] != expected_previous_hash:
            return position
        if compute_entry_hash(expected_previous_hash, entry) != entry["entry_hash"]:
            return position
        expected_previous_hash = str(entry["entry_hash"])
        expected_position += 1
    return None
