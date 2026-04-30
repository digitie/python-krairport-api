"""Exception hierarchy for pykrairport."""

from __future__ import annotations


class KrairportError(Exception):
    """Base exception for all pykrairport errors."""


class KrairportAuthError(KrairportError):
    """Authentication failed or a service key is missing/invalid."""


class KrairportRequestError(KrairportError):
    """The request parameters are invalid for the selected provider."""


class KrairportRateLimitError(KrairportError):
    """The provider rejected the request due to quota/rate limits."""


class KrairportNetworkError(KrairportError):
    """A network error occurred while calling a provider."""


class KrairportServerError(KrairportError):
    """The provider returned a server-side or otherwise unexpected error."""


class KrairportParseError(KrairportError):
    """A provider response could not be parsed into the expected structure."""


class UnsupportedAirportError(KrairportRequestError):
    """The requested airport/provider combination is not supported."""
