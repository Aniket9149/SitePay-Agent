#Owner::ANIKET::ANHOTRA = MR.Panda
"""Turns unfinished or optional features on and off safely.

Only flags listed in KNOWN_FEATURE_FLAGS exist. A typo in a flag name is an error,
never a silent "off", so a feature is never disabled or enabled by accident.
"""

from __future__ import annotations

from app.errors import ConfigurationError

# Every flag defaults to off. Add a flag here before using it anywhere.
KNOWN_FEATURE_FLAGS: dict[str, str] = {
    "password_reset": "Self service password reset by email (needs email delivery).",
    "face_blur": "Automatic face blurring in site photos.",
    "ai_extraction": "Model based extraction of facts from evidence.",
}


class FeatureFlags:
    """An immutable set of enabled feature flags."""

    def __init__(self, enabled_flag_names: frozenset[str]) -> None:
        """Store the enabled names after checking each one is a known flag.

        Raises ConfigurationError for any unknown name.
        """
        unknown_names = sorted(enabled_flag_names - KNOWN_FEATURE_FLAGS.keys())
        if unknown_names:
            raise ConfigurationError("Unknown feature flag: " + ", ".join(unknown_names))
        self._enabled_flag_names = enabled_flag_names

    @classmethod
    def from_text(cls, comma_separated_names: str) -> FeatureFlags:
        """Build flags from text such as "face_blur,ai_extraction".

        Blank entries and surrounding spaces are ignored.
        """
        names = frozenset(
            part.strip() for part in comma_separated_names.split(",") if part.strip() != ""
        )
        return cls(names)

    def is_enabled(self, flag_name: str) -> bool:
        """Return True when the named flag is on.

        Asking about an unknown flag raises ConfigurationError.
        """
        if flag_name not in KNOWN_FEATURE_FLAGS:
            raise ConfigurationError(f"Unknown feature flag: {flag_name}")
        return flag_name in self._enabled_flag_names

    def enabled_names(self) -> list[str]:
        """Return the enabled flag names in alphabetical order.

        Useful for the health report and for tests.
        """
        return sorted(self._enabled_flag_names)
