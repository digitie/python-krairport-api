from __future__ import annotations

import pytest

from krairport import Coordinate
from krairport.airports import (
    KAC_AIRPORTS,
    get_airport,
    get_airport_or_none,
    list_airports,
    nearest_airport,
)
from krairport.enums import Airport, AirportType, Provider
from krairport.exceptions import UnsupportedAirportError


def test_get_airport_returns_standard_metadata() -> None:
    airport = get_airport(Airport.ICN)

    assert airport.code == "ICN"
    assert airport.provider is Provider.IIAC
    assert airport.icao_code == "RKSI"
    assert airport.coordinate is not None
    assert airport.coordinate.as_geojson_position() == (126.450996, 37.469101)


def test_airport_registry_filters_provider_and_active_status() -> None:
    kac_airports = list_airports(provider=Provider.KAC, active=True)
    inactive = list_airports(active=False)

    assert "GMP" in KAC_AIRPORTS
    assert all(airport.provider is Provider.KAC for airport in kac_airports)
    assert all(airport.active for airport in kac_airports)
    assert inactive[0].code == "MPK"
    assert inactive[0].airport_type is AirportType.CLOSED


def test_nearest_airport_uses_standardized_coordinates() -> None:
    coordinate = Coordinate.from_values("37.56 N", "126.79 E")
    airport = nearest_airport(coordinate)

    assert airport is not None
    assert airport.code == "GMP"


def test_airport_lookup_handles_unsupported_codes() -> None:
    assert get_airport_or_none("bad") is None
    with pytest.raises(UnsupportedAirportError):
        get_airport("AAA")
