#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tests for the attempt tracker and the login and registration throttles.

A fake clock is used so nothing waits. These run for real without any web framework.
"""

from __future__ import annotations

import threading

import pytest

from app.errors import RateLimitedError
from app.security.attempt_tracker import AttemptTracker
from app.security.login_throttle import LoginThrottle, RegistrationThrottle


class FakeClock:
    """A clock that only moves when the test says so."""

    def __init__(self) -> None:
        """Start at time zero.

        Call advance to move forward.
        """
        self.now = 0.0

    def __call__(self) -> float:
        """Return the current fake time in seconds.

        Matches the callable the trackers expect.
        """
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake time forward by the given seconds.

        Never moves backwards.
        """
        self.now += seconds


def make_tracker(clock: FakeClock, **overrides: int) -> AttemptTracker:
    """Build a tracker of 3 events, 60 second window and 120 second lockout.

    Any value can be overridden by the test.
    """
    settings = {"maximum_events": 3, "window_seconds": 60, "lockout_seconds": 120}
    settings.update(overrides)
    return AttemptTracker(clock=clock, **settings)


def test_tracker_locks_at_the_maximum_and_reports_wait_time() -> None:
    """The third event locks the key, and the wait is the full lockout."""
    clock = FakeClock()
    tracker = make_tracker(clock)
    for _ in range(2):
        tracker.record_event("k")
        tracker.ensure_not_locked("k")
    tracker.record_event("k")
    with pytest.raises(RateLimitedError) as caught:
        tracker.ensure_not_locked("k")
    assert caught.value.retry_after_seconds == 120
    assert caught.value.status_code == 429


def test_wait_time_shrinks_and_rounds_up() -> None:
    """After 30.5 seconds there are 89.5 seconds left, reported as 90."""
    clock = FakeClock()
    tracker = make_tracker(clock)
    for _ in range(3):
        tracker.record_event("k")
    clock.advance(30.5)
    with pytest.raises(RateLimitedError) as caught:
        tracker.ensure_not_locked("k")
    assert caught.value.retry_after_seconds == 90


def test_lock_expires_exactly_at_the_end() -> None:
    """One second before the end it is locked, at the end it is open again."""
    clock = FakeClock()
    tracker = make_tracker(clock)
    for _ in range(3):
        tracker.record_event("k")
    clock.advance(119)
    with pytest.raises(RateLimitedError):
        tracker.ensure_not_locked("k")
    clock.advance(1)
    tracker.ensure_not_locked("k")


def test_old_events_fall_out_of_the_window() -> None:
    """Two events, then a long pause, then one event is not enough to lock."""
    clock = FakeClock()
    tracker = make_tracker(clock)
    tracker.record_event("k")
    tracker.record_event("k")
    clock.advance(60)
    tracker.record_event("k")
    tracker.ensure_not_locked("k")


def test_events_while_locked_do_not_extend_the_lock() -> None:
    """Hammering a locked key does not push the end time further away."""
    clock = FakeClock()
    tracker = make_tracker(clock)
    for _ in range(3):
        tracker.record_event("k")
    clock.advance(100)
    for _ in range(50):
        tracker.record_event("k")
    clock.advance(20)
    tracker.ensure_not_locked("k")


def test_keys_are_independent_and_reset_works() -> None:
    """One key's lock does not affect another, and reset forgets a key."""
    clock = FakeClock()
    tracker = make_tracker(clock)
    for _ in range(3):
        tracker.record_event("a")
    tracker.ensure_not_locked("b")
    tracker.reset("a")
    tracker.ensure_not_locked("a")
    tracker.reset("never-seen")


@pytest.mark.parametrize("field", ["maximum_events", "window_seconds", "lockout_seconds", "maximum_tracked_keys"])
def test_tracker_rejects_non_positive_limits(field: str) -> None:
    """Zero or negative limits are a programming error."""
    for bad_value in (0, -1):
        with pytest.raises(ValueError):
            make_tracker(FakeClock(), **{field: bad_value})


def test_memory_is_capped_and_idle_keys_go_first() -> None:
    """Flooding with new keys never exceeds the cap, and a locked key survives the flood."""
    clock = FakeClock()
    tracker = make_tracker(clock, maximum_events=2, maximum_tracked_keys=5)
    tracker.record_event("locked")
    tracker.record_event("locked")
    for number in range(50):
        tracker.record_event(f"flood-{number}")
    assert tracker.tracked_key_count() <= 5
    with pytest.raises(RateLimitedError):
        tracker.ensure_not_locked("locked")


def test_expired_keys_are_cleaned_when_over_the_cap() -> None:
    """Once everything has expired, new keys push the old idle ones out first."""
    clock = FakeClock()
    tracker = make_tracker(clock, maximum_events=5, maximum_tracked_keys=3)
    for name in ("a", "b", "c"):
        tracker.record_event(name)
    clock.advance(1000)
    tracker.record_event("d")
    assert tracker.tracked_key_count() == 1


def test_tracker_is_safe_under_concurrent_use() -> None:
    """Ten threads each record ten events. Exactly the hundredth event locks the key."""
    clock = FakeClock()
    tracker = make_tracker(clock, maximum_events=100, window_seconds=1000, lockout_seconds=1000)

    def record_ten() -> None:
        """Record ten events for the shared key.

        Runs inside one worker thread.
        """
        for _ in range(10):
            tracker.record_event("shared")

    threads = [threading.Thread(target=record_ten) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    with pytest.raises(RateLimitedError):
        tracker.ensure_not_locked("shared")


def make_login_throttle(clock: FakeClock) -> LoginThrottle:
    """Build a login throttle with 3 failures allowed and a 100 second lockout.

    The address limit is then 12.
    """
    return LoginThrottle(maximum_failures=3, lockout_seconds=100, clock=clock)


def fail_times(throttle: LoginThrottle, email: str, address: str, times: int) -> None:
    """Record the given number of failed logins.

    Used to keep the tests short.
    """
    for _ in range(times):
        throttle.register_failure(email, address)


def test_repeated_failures_lock_that_email_and_address_pair() -> None:
    """Three failures lock the pair, and the email is matched ignoring case and spaces."""
    throttle = make_login_throttle(FakeClock())
    fail_times(throttle, "Owner@Example.com", "1.1.1.1", 3)
    with pytest.raises(RateLimitedError):
        throttle.ensure_allowed(" owner@example.com ", "1.1.1.1")


def test_another_address_cannot_be_used_to_lock_out_the_real_owner() -> None:
    """An attacker's failures on one address do not block the same email from another address."""
    throttle = make_login_throttle(FakeClock())
    fail_times(throttle, "owner@example.com", "6.6.6.6", 3)
    throttle.ensure_allowed("owner@example.com", "2.2.2.2")


def test_one_address_trying_many_emails_gets_locked_at_the_address_limit() -> None:
    """Twelve failures across different emails lock the whole address."""
    throttle = make_login_throttle(FakeClock())
    for number in range(12):
        throttle.ensure_allowed(f"user{number}@example.com", "3.3.3.3")
        throttle.register_failure(f"user{number}@example.com", "3.3.3.3")
    with pytest.raises(RateLimitedError):
        throttle.ensure_allowed("another@example.com", "3.3.3.3")
    throttle.ensure_allowed("another@example.com", "4.4.4.4")


def test_success_clears_the_pair_but_not_the_address_count() -> None:
    """A good login resets the pair, but cannot be used to reset the address count."""
    throttle = make_login_throttle(FakeClock())
    fail_times(throttle, "me@example.com", "5.5.5.5", 2)
    throttle.register_success("me@example.com", "5.5.5.5")
    fail_times(throttle, "me@example.com", "5.5.5.5", 2)
    throttle.ensure_allowed("me@example.com", "5.5.5.5")
    for number in range(4):
        fail_times(throttle, f"victim{number}@example.com", "5.5.5.5", 2)
    throttle.register_success("me@example.com", "5.5.5.5")
    with pytest.raises(RateLimitedError):
        throttle.ensure_allowed("fresh@example.com", "5.5.5.5")


def test_login_lock_expires() -> None:
    """After the lockout time the same email and address can try again."""
    clock = FakeClock()
    throttle = make_login_throttle(clock)
    fail_times(throttle, "owner@example.com", "1.1.1.1", 3)
    clock.advance(100)
    throttle.ensure_allowed("owner@example.com", "1.1.1.1")


def test_locked_and_unlocked_attempts_look_the_same_for_unknown_emails() -> None:
    """Failures count for emails nobody registered, so the lock never reveals which emails exist."""
    throttle = make_login_throttle(FakeClock())
    fail_times(throttle, "nobody@example.com", "1.1.1.1", 3)
    with pytest.raises(RateLimitedError) as unknown:
        throttle.ensure_allowed("nobody@example.com", "1.1.1.1")
    fail_times(throttle, "real@example.com", "1.1.1.1", 3)
    with pytest.raises(RateLimitedError) as real:
        throttle.ensure_allowed("real@example.com", "1.1.1.1")
    assert unknown.value.to_response_body()["error"]["message"] == real.value.to_response_body()["error"]["message"]


def test_registration_allows_the_limit_then_blocks_and_recovers() -> None:
    """Ten per hour are allowed, the eleventh is refused, and an hour later it works again."""
    clock = FakeClock()
    throttle = RegistrationThrottle(maximum_per_hour=10, clock=clock)
    for _ in range(10):
        throttle.register_attempt("7.7.7.7")
    with pytest.raises(RateLimitedError):
        throttle.register_attempt("7.7.7.7")
    throttle.register_attempt("8.8.8.8")
    clock.advance(3600)
    throttle.register_attempt("7.7.7.7")
