"""Shared enums for pykrairport."""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    """Airport API provider."""

    KAC = "kac"
    IIAC = "iiac"


class Direction(StrEnum):
    """Flight direction."""

    ARRIVAL = "arrival"
    DEPARTURE = "departure"


class Airport(StrEnum):
    """Supported Korean IATA airport codes."""

    ICN = "ICN"
    GMP = "GMP"
    PUS = "PUS"
    CJU = "CJU"
    TAE = "TAE"
    CJJ = "CJJ"
    KWJ = "KWJ"
    RSU = "RSU"
    USN = "USN"
    MWX = "MWX"
    YNY = "YNY"
    KUV = "KUV"
    HIN = "HIN"
    WJU = "WJU"
    KPO = "KPO"
    MPK = "MPK"


class AirportType(StrEnum):
    """Airport size/type category used by the bundled airport registry."""

    LARGE = "large_airport"
    MEDIUM = "medium_airport"
    SMALL = "small_airport"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class ApiLanguage(StrEnum):
    """Language code accepted by provider APIs when a language parameter exists."""

    KOREAN = "K"
    ENGLISH = "E"
    JAPANESE = "J"
    CHINESE = "C"


class ScheduleType(StrEnum):
    """Regular flight schedule scope."""

    DOMESTIC = "domestic"
    INTERNATIONAL = "international"


class CoordinateDatum(StrEnum):
    """Coordinate reference datum exposed by pykrairport."""

    WGS84 = "WGS84"


def normalize_provider(value: str | Provider) -> Provider:
    """Normalize a provider-like value to `Provider`."""

    return Provider(str(value).strip().lower())


def normalize_direction(value: str | Direction) -> Direction:
    """Normalize a direction-like value to `Direction`."""

    return Direction(str(value).strip().lower())
