"""Python client for Korean airport public APIs."""

from pykrairport.client import KrairportClient
from pykrairport.exceptions import (
    KrairportAuthError,
    KrairportError,
    KrairportNetworkError,
    KrairportParseError,
    KrairportRateLimitError,
    KrairportRequestError,
    KrairportServerError,
    UnsupportedAirportError,
)
from pykrairport.models import (
    AircraftAssignment,
    ArrivalCongestion,
    Flight,
    ParkingAreaStatus,
    ParkingFee,
    PassengerForecast,
)

__version__ = "0.1.0"

__all__ = [
    "AircraftAssignment",
    "ArrivalCongestion",
    "Flight",
    "KrairportAuthError",
    "KrairportClient",
    "KrairportError",
    "KrairportNetworkError",
    "KrairportParseError",
    "KrairportRateLimitError",
    "KrairportRequestError",
    "KrairportServerError",
    "ParkingAreaStatus",
    "ParkingFee",
    "PassengerForecast",
    "UnsupportedAirportError",
    "__version__",
]
