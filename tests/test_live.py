from __future__ import annotations

import os

import pytest

from krairport.client import KrairportClient
from krairport.config import KrairportConfig
from krairport.exceptions import KrairportAuthError, KrairportServerError


def _require_live_key(request: pytest.FixtureRequest, marker: str, env_name: str) -> str:
    markexpr = request.config.option.markexpr or ""
    if marker not in markexpr:
        pytest.skip(f"run explicitly with -m {marker}")
    config = KrairportConfig.from_env()
    value = os.environ.get(env_name) or getattr(
        config,
        "kac_service_key" if env_name == "KAC_SERVICE_KEY" else "iiac_service_key",
    )
    if not value:
        pytest.skip(f"{env_name} is not set")
    return value


def _skip_unapproved_live_service(exc: Exception) -> None:
    message = str(exc).upper()
    if isinstance(exc, KrairportAuthError) or "SERVICE ACCESS DENIED" in message:
        pytest.skip(f"live service key is not approved for this endpoint: {exc}")
    if isinstance(exc, KrairportServerError) and "NO OPENAPI SERVICE" in message:
        pytest.skip(f"live service is not accessible with the configured key: {exc}")
    raise exc


@pytest.mark.live_kac
def test_live_kac_departures_smoke(request: pytest.FixtureRequest) -> None:
    service_key = _require_live_key(request, "live_kac", "KAC_SERVICE_KEY")
    client = KrairportClient(kac_service_key=service_key, iiac_service_key=None, retries=0)

    try:
        rows = client.departures(airport_code="GMP", num_of_rows=1)
    except (KrairportAuthError, KrairportServerError) as exc:
        _skip_unapproved_live_service(exc)

    assert isinstance(rows, list)
    if rows:
        assert rows[0].flight_id
        assert rows[0].raw


@pytest.mark.live_iiac
def test_live_iiac_parking_status_smoke(request: pytest.FixtureRequest) -> None:
    service_key = _require_live_key(request, "live_iiac", "IIAC_SERVICE_KEY")
    client = KrairportClient(kac_service_key=None, iiac_service_key=service_key, retries=0)

    try:
        rows = client.parking_status(num_of_rows=1)
    except (KrairportAuthError, KrairportServerError) as exc:
        _skip_unapproved_live_service(exc)

    assert isinstance(rows, list)
    if rows:
        assert rows[0].raw
