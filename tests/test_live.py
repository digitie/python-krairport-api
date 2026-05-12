from __future__ import annotations

import os

import pytest

from krairport.client import KrairportClient


def _require_live_key(request: pytest.FixtureRequest, marker: str, env_name: str) -> str:
    markexpr = request.config.option.markexpr or ""
    if marker not in markexpr:
        pytest.skip(f"run explicitly with -m {marker}")
    value = os.environ.get(env_name)
    if not value:
        pytest.skip(f"{env_name} is not set")
    return value


@pytest.mark.live_kac
def test_live_kac_airport_codes_smoke(request: pytest.FixtureRequest) -> None:
    service_key = _require_live_key(request, "live_kac", "KAC_SERVICE_KEY")
    client = KrairportClient(kac_service_key=service_key, iiac_service_key=None, retries=0)

    rows = client.airport_codes(code="GMP", num_of_rows=1)

    assert isinstance(rows, list)
    if rows:
        assert rows[0].code
        assert rows[0].raw


@pytest.mark.live_iiac
def test_live_iiac_service_destinations_smoke(request: pytest.FixtureRequest) -> None:
    service_key = _require_live_key(request, "live_iiac", "IIAC_SERVICE_KEY")
    client = KrairportClient(kac_service_key=None, iiac_service_key=service_key, retries=0)

    rows = client.service_destinations(num_of_rows=1)

    assert isinstance(rows, list)
    if rows:
        assert rows[0].raw
