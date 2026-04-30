"""Airport provider routing."""

from __future__ import annotations

from pykrairport._convert import normalize_airport_code
from pykrairport.exceptions import UnsupportedAirportError

KAC_AIRPORTS = frozenset(
    {
        "GMP",
        "PUS",
        "CJU",
        "TAE",
        "CJJ",
        "KWJ",
        "RSU",
        "USN",
        "MWX",
        "YNY",
        "KUV",
        "HIN",
        "WJU",
        "KPO",
        "MPK",
    }
)


def provider_for_airport(airport_code: str) -> str:
    code = normalize_airport_code(airport_code)
    if code == "ICN":
        return "iiac"
    if code in KAC_AIRPORTS:
        return "kac"
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
