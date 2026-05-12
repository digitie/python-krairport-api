"""krairport 공용 enum."""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    """공항 API 공급자."""

    KAC = "kac"
    IIAC = "iiac"


class Direction(StrEnum):
    """항공편 운항 방향."""

    ARRIVAL = "arrival"
    DEPARTURE = "departure"


class Airport(StrEnum):
    """지원하는 한국 IATA 공항코드."""

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
    """번들 공항 레지스트리에서 사용하는 공항 규모/유형."""

    LARGE = "large_airport"
    MEDIUM = "medium_airport"
    SMALL = "small_airport"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class ApiLanguage(StrEnum):
    """언어 파라미터가 있는 공급자 API에서 사용하는 언어 코드."""

    KOREAN = "K"
    ENGLISH = "E"
    JAPANESE = "J"
    CHINESE = "C"


class ScheduleType(StrEnum):
    """정기 운항스케줄 범위."""

    DOMESTIC = "domestic"
    INTERNATIONAL = "international"


class CoordinateDatum(StrEnum):
    """krairport가 노출하는 좌표 기준계."""

    WGS84 = "WGS84"


def normalize_provider(value: str | Provider) -> Provider:
    """공급자 유사 값을 `Provider`로 정규화합니다."""

    return Provider(str(value).strip().lower())


def normalize_direction(value: str | Direction) -> Direction:
    """운항 방향 유사 값을 `Direction`으로 정규화합니다."""

    return Direction(str(value).strip().lower())
