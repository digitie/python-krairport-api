from __future__ import annotations

import pykrairport
from pykrairport.enums import Direction, Provider


def test_public_exports() -> None:
    assert pykrairport.__version__ == "0.1.0"
    assert hasattr(pykrairport, "KrairportClient")
    assert hasattr(pykrairport, "Flight")


def test_enum_values() -> None:
    assert Provider.KAC == "kac"
    assert Provider.IIAC == "iiac"
    assert Direction.ARRIVAL == "arrival"
    assert Direction.DEPARTURE == "departure"
