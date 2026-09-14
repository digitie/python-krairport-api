from __future__ import annotations

import pytest

from krairport.client import KrairportClient
from krairport.config import KrairportConfig
from krairport.exceptions import KrairportAuthError, KrairportServerError


def _require_live_key(request: pytest.FixtureRequest, marker: str) -> str:
    markexpr = request.config.option.markexpr or ""
    if marker not in markexpr:
        pytest.skip(f"run explicitly with -m {marker}")
    config = KrairportConfig.from_env()
    value = config.kac_service_key
    if not value:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is not set")
    return value


def _skip_unapproved_live_service(exc: Exception) -> None:
    message = str(exc).upper()
    if isinstance(exc, KrairportAuthError) or "SERVICE ACCESS DENIED" in message:
        pytest.skip(f"live service key is not approved for this endpoint: {exc}")
    if isinstance(exc, KrairportServerError) and "NO OPENAPI SERVICE" in message:
        pytest.skip(f"live service is not accessible with the configured key: {exc}")
    raise exc


@pytest.mark.live_kac
async def test_live_kac_departures_smoke(request: pytest.FixtureRequest) -> None:
    service_key = _require_live_key(request, "live_kac")
    async with KrairportClient(
        kac_service_key=service_key, iiac_service_key=None, retries=0
    ) as client:
        try:
            rows = await client.departures(airport_code="GMP", num_of_rows=1)
        except (KrairportAuthError, KrairportServerError) as exc:
            _skip_unapproved_live_service(exc)

        assert isinstance(rows, list)
        if rows:
            assert rows[0].flight_id
            assert rows[0].raw


@pytest.mark.live_iiac
async def test_live_iiac_parking_status_smoke(request: pytest.FixtureRequest) -> None:
    service_key = _require_live_key(request, "live_iiac")
    async with KrairportClient(
        kac_service_key=None, iiac_service_key=service_key, retries=0
    ) as client:
        try:
            rows = await client.parking_status(num_of_rows=1)
        except (KrairportAuthError, KrairportServerError) as exc:
            _skip_unapproved_live_service(exc)

        assert isinstance(rows, list)
        assert rows
        assert rows[0].raw


@pytest.mark.live_kac
async def test_live_kac_parking_fees_returns_data(request: pytest.FixtureRequest) -> None:
    key = _require_live_key(request, "live_kac")
    async with KrairportClient(kac_service_key=key, retries=0) as client:
        fees = await client.parking_fees(airport_code="GMP")
    assert fees
    assert fees[0].airport_code == "GMP"
    assert fees[0].raw
