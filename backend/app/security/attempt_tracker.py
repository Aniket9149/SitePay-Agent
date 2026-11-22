#Owner::ANIKET::ANHOTRA = MR.Panda
"""Counts events per key and locks the key for a while when there are too many.

State lives in memory in this one process. With several server processes each has its own
counts, so the real limit is multiplied by the number of processes. A shared store (the database
or Redis) is the planned fix, and is recorded in docs/08_security_privacy.md. Memory is capped so
an attacker cannot fill it with made up keys.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from app.errors import RateLimitedError

DEFAULT_MAXIMUM_TRACKED_KEYS = 10_000


@dataclass
class _KeyState:
    """What is remembered about one key: recent event times and any lock end time."""

    event_times: deque[float] = field(default_factory=deque)
    locked_until: float = 0.0


class AttemptTracker:
    """Locks a key once it has recorded the maximum number of events within the window."""

    def __init__(
        self,
        *,
        maximum_events: int,
        window_seconds: int,
        lockout_seconds: int,
        clock: Callable[[], float] = time.monotonic,
        maximum_tracked_keys: int = DEFAULT_MAXIMUM_TRACKED_KEYS,
    ) -> None:
        """Set the limits. All numbers must be positive, or ValueError is raised.

        The clock can be replaced in tests so no test needs to wait.
        """
        if min(maximum_events, window_seconds, lockout_seconds, maximum_tracked_keys) < 1:
            raise ValueError("Every limit must be at least 1.")
        self._maximum_events = maximum_events
        self._window_seconds = window_seconds
        self._lockout_seconds = lockout_seconds
        self._clock = clock
        self._maximum_tracked_keys = maximum_tracked_keys
        self._states: dict[str, _KeyState] = {}
        self._lock = threading.Lock()

    def ensure_not_locked(self, key: str) -> None:
        """Raise RateLimitedError with the wait time when the key is currently locked.

        Does nothing for unknown keys, and an expired lock no longer blocks.
        """
        with self._lock:
            state = self._states.get(key)
            now = self._clock()
            if state is not None and state.locked_until > now:
                raise RateLimitedError(math.ceil(state.locked_until - now))

    def record_event(self, key: str) -> None:
        """Count one event for the key, and lock the key when the maximum is reached.

        Events recorded while the key is already locked are ignored.
        """
        with self._lock:
            now = self._clock()
            state = self._states.setdefault(key, _KeyState())
            if state.locked_until > now:
                return
            self._drop_old_events(state, now)
            state.event_times.append(now)
            if len(state.event_times) >= self._maximum_events:
                state.locked_until = now + self._lockout_seconds
                state.event_times.clear()
            self._enforce_capacity(now)

    def reset(self, key: str) -> None:
        """Forget the key completely, for example after a successful login.

        Does nothing for unknown keys.
        """
        with self._lock:
            self._states.pop(key, None)

    def tracked_key_count(self) -> int:
        """Return how many keys are remembered right now.

        Used by tests to prove the memory cap holds.
        """
        with self._lock:
            return len(self._states)

    def _drop_old_events(self, state: _KeyState, now: float) -> None:
        """Remove events older than the window from the state.

        The caller must hold the lock.
        """
        while state.event_times and now - state.event_times[0] >= self._window_seconds:
            state.event_times.popleft()

    def _is_idle(self, state: _KeyState, now: float) -> bool:
        """Return True when the key has no active lock and no recent events.

        Idle keys are safe to forget. The caller must hold the lock.
        """
        self._drop_old_events(state, now)
        return state.locked_until <= now and not state.event_times

    def _enforce_capacity(self, now: float) -> None:
        """Keep the number of remembered keys at or under the cap.

        Forgets idle keys first, then the oldest unlocked keys, and locked keys only as a
        last resort.
        """
        if len(self._states) <= self._maximum_tracked_keys:
            return
        for key in [key for key, state in self._states.items() if self._is_idle(state, now)]:
            del self._states[key]
        while len(self._states) > self._maximum_tracked_keys:
            unlocked_keys = [k for k, s in self._states.items() if s.locked_until <= now]
            del self._states[unlocked_keys[0] if unlocked_keys else next(iter(self._states))]
