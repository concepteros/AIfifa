from __future__ import annotations

class PredictAPIError(Exception):
    """Base exception for Predict API client errors."""


class PredictConfigError(PredictAPIError):
    """Raised when API configuration is incomplete or invalid."""


class PredictValidationError(PredictAPIError):
    """Raised when user input is invalid."""


class PredictAuthenticationError(PredictAPIError):
    """Raised when the API rejects authentication."""


class PredictHTTPError(PredictAPIError):
    """Raised for non-authentication HTTP failures."""

    def __init__(self, status_code: int, message: str, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class PredictResponseError(PredictAPIError):
    """Raised when the API returns an unexpected response shape."""
