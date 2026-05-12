from __future__ import annotations

import krairport
from krairport.enums import Airport, Direction, Provider


def test_public_exports() -> None:
    assert krairport.__version__ == "0.1.0"
    assert hasattr(krairport, "Address")
    assert hasattr(krairport, "KrairportClient")
    assert hasattr(krairport, "Flight")
    assert hasattr(krairport, "PlaceCoordinate")
    assert hasattr(krairport, "AirportMetadata")
    assert hasattr(krairport, "get_airport")


def test_enum_values() -> None:
    assert Provider.KAC == "kac"
    assert Provider.IIAC == "iiac"
    assert Direction.ARRIVAL == "arrival"
    assert Direction.DEPARTURE == "departure"
    assert Airport.ICN == "ICN"
    assert Airport.GMP == "GMP"
