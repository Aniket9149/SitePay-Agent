#Owner::ANIKET::ANHOTRA = MR.Panda
"""Slows down password guessing and mass account creation.

Login failures are counted two ways. Per email and address together, so one attacker cannot lock
the real owner out from another address. And per address alone with a higher limit, so one address
cannot try endless different emails. A guess across many addresses at once is not stopped by this,
which is why the shared store and alerting are planned later. A locked key is refused even when the
password is right, because otherwise the lock would not stop guessing.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from app.security.attempt_tracker import AttemptTracker

ADDRESS_FAILURE_MULTIPLIER = 4
REGISTRATION_WINDOW_SECONDS = 3600


class LoginThrottle:
    """Tracks failed logins and refuses further attempts while a key is locked."""

    def __init__(
        self,
        *,
        maximum_failures: int,
        lockout_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create the two trackers: one for email and address, one for the address alone.

        The address limit is four times the pair limit.
        """
        self._pair_tracker = AttemptTracker(
            maximum_events=maximum_failures,
            window_seconds=lockout_seconds,
            lockout_seconds=lockout_seconds,
            clock=clock,
        )
        self._address_tracker = AttemptTracker(
            maximum_events=maximum_failures * ADDRESS_FAILURE_MULTIPLIER,
            window_seconds=lockout_seconds,
            lockout_seconds=lockout_seconds,
            clock=clock,
        )

    @staticmethod
    def _pair_key(email: str, client_address: str) -> str:
        """Build the combined key, with the email trimmed and lowercased.

        So "A@x.com" and "a@x.com " count together.
        """
        return f"{email.strip().lower()}|{client_address}"

    def ensure_allowed(self, email: str, client_address: str) -> None:
        """Raise RateLimitedError when this address or this email and address pair is locked.

        Call before checking the password.
        """
        self._address_tracker.ensure_not_locked(client_address)
        self._pair_tracker.ensure_not_locked(self._pair_key(email, client_address))

    def register_failure(self, email: str, client_address: str) -> None:
        """Count a failed login against both the pair and the address.

        Unknown emails count too, so the limit does not reveal which emails exist.
        """
        self._pair_tracker.record_event(self._pair_key(email, client_address))
        self._address_tracker.record_event(client_address)

    def register_success(self, email: str, client_address: str) -> None:
        """Clear the pair after a good login, but not the address count.

        Otherwise an attacker with their own account could reset the address count at will.
        """
        self._pair_tracker.reset(self._pair_key(email, client_address))


class RegistrationThrottle:
    """Limits how many accounts one address may create per hour."""

    def __init__(
        self, *, maximum_per_hour: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        """Create the tracker. Going over the limit locks the address for an hour.

        The hour is fixed because account creation is rare for real people.
        """
        self._tracker = AttemptTracker(
            maximum_events=maximum_per_hour,
            window_seconds=REGISTRATION_WINDOW_SECONDS,
            lockout_seconds=REGISTRATION_WINDOW_SECONDS,
            clock=clock,
        )

    def register_attempt(self, client_address: str) -> None:
        """Refuse the attempt if the address is locked, otherwise count it.

        Raises RateLimitedError when the address has reached its limit.
        """
        self._tracker.ensure_not_locked(client_address)
        self._tracker.record_event(client_address)
