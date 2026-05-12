"""공항 공급자 라우팅."""

from __future__ import annotations

from krairport._convert import normalize_airport_code
from krairport.airports import KAC_AIRPORTS
from krairport.enums import Provider
from krairport.exceptions import UnsupportedAirportError


def provider_for_airport(airport_code: str) -> Provider:
    code = normalize_airport_code(airport_code)
    if code == "ICN":
        return Provider.IIAC
    if code in KAC_AIRPORTS:
        return Provider.KAC
    raise UnsupportedAirportError(f"unsupported Korean airport code: {airport_code!r}")


def ensure_kac_airport(airport_code: str) -> str:
    code = normalize_airport_code(airport_code)
    if code == "ICN":
        raise UnsupportedAirportError("ICN is served by IIAC, not KAC")
    if code not in KAC_AIRPORTS:
        raise UnsupportedAirportError(f"KAC airport is not supported: {airport_code!r}")
    return code


def ensure_iiac_airport(airport_code: str = "ICN") -> str:
    code = normalize_airport_code(airport_code)
    if code != "ICN":
        raise UnsupportedAirportError("IIAC-only APIs support ICN only")
    return code
