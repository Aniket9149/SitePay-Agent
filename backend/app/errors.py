#Owner::ANIKET::ANHOTRA = MR.Panda
"""Custom error classes with clear messages and stable machine readable codes.

This module has no framework imports so it can be used and tested anywhere.
The web layer turns these errors into JSON responses.
"""

from __future__ import annotations

from typing import Any


class SitePayError(Exception):
    """Base class for every expected application error.

    Carries an HTTP status, a stable error code, a plain message and optional details.
    """

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        """Store the plain language message and optional structured details.

        The message is safe to show to the user, so never put secrets in it.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_response_body(self) -> dict[str, Any]:
        """Return the JSON body sent to the client for this error.

        The shape is the same for every error so the frontend can handle it once.
        """
        body: dict[str, Any] = {"code": self.error_code, "message": self.message}
        if self.details:
            body["details"] = self.details
        return {"error": body}


class ConfigurationError(SitePayError):
    """Raised when required settings are missing or unsafe."""

    status_code = 500
    error_code = "configuration_error"


class AuthenticationError(SitePayError):
    """Raised when the person could not be identified."""

    status_code = 401
    error_code = "authentication_failed"


class PermissionDeniedError(SitePayError):
    """Raised when the person is known but not allowed to do this."""

    status_code = 403
    error_code = "permission_denied"


class NotFoundError(SitePayError):
    """Raised when a record does not exist or is not visible to this organisation."""

    status_code = 404
    error_code = "not_found"


class ConflictError(SitePayError):
    """Raised when the request clashes with existing data."""

    status_code = 409
    error_code = "conflict"


class AuditLogImmutableError(SitePayError):
    """Raised when code tries to change or delete an audit log entry."""

    status_code = 500
    error_code = "audit_log_immutable"


class DomainValidationError(SitePayError):
    """Raised when data is well formed but breaks a business rule."""

    status_code = 422
    error_code = "validation_failed"
