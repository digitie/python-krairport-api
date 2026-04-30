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
    AirportCode,
    AirportFacility,
    ArrivalCongestion,
    BusRoute,
    Flight,
    FlightSchedule,
    ParkingAreaStatus,
    ParkingFee,
    PassengerForecast,
    ServiceDestination,
    TaxiStatus,
    WorldWeather,
)

__version__ = "0.1.0"

__all__ = [
    "AircraftAssignment",
    "AirportCode",
    "AirportFacility",
    "ArrivalCongestion",
    "BusRoute",
    "FlightSchedule",
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
    "ServiceDestination",
    "TaxiStatus",
    "UnsupportedAirportError",
    "WorldWeather",
    "__version__",
]
