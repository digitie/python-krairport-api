from __future__ import annotations

import pytest

from krairport._routing import ensure_iiac_airport, ensure_kac_airport, provider_for_airport
from krairport.exceptions import UnsupportedAirportError


def test_icn_routes_to_iiac() -> None:
    assert provider_for_airport("icn") == "iiac"


def test_kac_airport_routes_to_kac() -> None:
    assert provider_for_airport("gmp") == "kac"
    assert provider_for_airport("cju") == "kac"


def test_icn_is_rejected_for_kac() -> None:
    with pytest.raises(UnsupportedAirportError):
        ensure_kac_airport("ICN")


def test_non_icn_is_rejected_for_iiac() -> None:
    with pytest.raises(UnsupportedAirportError):
        ensure_iiac_airport("GMP")
