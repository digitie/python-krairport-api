from __future__ import annotations

import krairport
from krairport.enums import Airport, Direction, Provider


def test_public_exports() -> None:
    assert krairport.__version__ == "0.1.0"
    assert hasattr(krairport, "Coordinate")
    assert hasattr(krairport, "AsyncKrairportClient")
    assert hasattr(krairport, "KrairportClient")
    assert hasattr(krairport, "KrairportConfig")
    assert hasattr(krairport, "Flight")
    assert hasattr(krairport, "to_decimal_degrees")
    assert hasattr(krairport, "AirportMetadata")
    assert hasattr(krairport, "PaginatedResult")
    assert krairport.PROVIDER_NAME == "python-krairport-api"
    assert hasattr(krairport, "api_catalog")
    assert hasattr(krairport, "ApiCatalogItem")
    assert hasattr(krairport, "get_airport")


def test_enum_values() -> None:
    assert Provider.KAC == "kac"
    assert Provider.IIAC == "iiac"
    assert Direction.ARRIVAL == "arrival"
    assert Direction.DEPARTURE == "departure"
    assert Airport.ICN == "ICN"
    assert Airport.GMP == "GMP"
