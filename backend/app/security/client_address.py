#Owner::ANIKET::ANHOTRA = MR.Panda
"""Finds the real client address, without trusting a header anyone can fake.

The X-Forwarded-For header is written by every proxy and can also be set by the client. So it
is used only when the number of trusted proxies in front of the server is configured, and then
only the entry added by the first trusted proxy is believed. With no trusted proxy configured the
direct connection address is always used. Without this, every user behind one proxy would share
one address and one lockout.
"""

from __future__ import annotations

import ipaddress

UNKNOWN_ADDRESS = "unknown"


def _is_valid_address(candidate: str) -> bool:
    """Return True when the text is a valid IPv4 or IPv6 address.

    Anything else is ignored, so junk in the header cannot become a tracking key.
    """
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return False
    return True


def extract_client_address(
    peer_host: str | None, forwarded_for: str | None, trusted_proxy_count: int
) -> str:
    """Return the address to count attempts against.

    Uses the header entry counted from the right by trusted_proxy_count, or the peer address.
    """
    fallback = peer_host if peer_host else UNKNOWN_ADDRESS
    if trusted_proxy_count <= 0 or not forwarded_for:
        return fallback
    entries = [entry.strip() for entry in forwarded_for.split(",") if entry.strip() != ""]
    if len(entries) < trusted_proxy_count:
        return fallback
    candidate = entries[-trusted_proxy_count]
    return candidate if _is_valid_address(candidate) else fallback
