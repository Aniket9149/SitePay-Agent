#Owner::ANIKET::ANHOTRA = MR.Panda
"""Shared paging convention for every list route in every workstream.

Fetch one more row than the limit. If it arrives there is another page, and it is dropped
before returning. This avoids a slow count query on large tables and works on weak mobile
connections. Existing Phase 1 list routes return plain lists and move to this envelope in a
later change, with a version note in docs/interface_contracts.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel, Field

DEFAULT_PAGE_LIMIT = 50
MAXIMUM_PAGE_LIMIT = 100

ItemType = TypeVar("ItemType")


class PageRequest(BaseModel):
    """Paging input accepted by every list route."""

    limit: int = Field(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAXIMUM_PAGE_LIMIT)
    offset: int = Field(default=0, ge=0)

    @property
    def fetch_limit(self) -> int:
        """How many rows a service should fetch: one more than the limit.

        The extra row only tells us whether another page exists.
        """
        return self.limit + 1


class Page[ItemType](BaseModel):
    """One page of results with what the client needs to ask for the next."""

    items: list[ItemType]
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None


def build_page[ItemType](fetched_rows: Sequence[ItemType], request: PageRequest) -> Page[ItemType]:
    """Turn rows fetched with fetch_limit into a Page.

    Drops the extra row and sets has_more and next_offset.
    """
    has_more = len(fetched_rows) > request.limit
    items = list(fetched_rows[: request.limit])
    return Page[ItemType](
        items=items,
        limit=request.limit,
        offset=request.offset,
        has_more=has_more,
        next_offset=request.offset + request.limit if has_more else None,
    )
