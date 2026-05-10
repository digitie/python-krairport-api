from __future__ import annotations

import pykrairport
from pykrairport.enums import Airport, Direction, Provider


def test_public_exports() -> None:
    assert pykrairport.__version__ == "0.1.0"
    assert hasattr(pykrairport, "Address")
    assert hasattr(pykrairport, "KrairportClient")
    assert hasattr(pykrairport, "Flight")
    assert hasattr(pykrairport, "PlaceCoordinate")
    assert hasattr(pykrairport, "AirportMetadata")
    assert hasattr(pykrairport, "get_airport")


def test_enum_values() -> None:
    assert Provider.KAC == "kac"
    assert Provider.IIAC == "iiac"
    assert Direction.ARRIVAL == "arrival"
    assert Direction.DEPARTURE == "departure"
    assert Airport.ICN == "ICN"
    assert Airport.GMP == "GMP"
