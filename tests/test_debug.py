from __future__ import annotations

from datetime import date

from krairport import DebugRun, KrairportClient, jsonable, redact_sensitive
from tests.conftest import FakeResponse, FakeSession


def test_debug_departures_returns_fixture_ready_run(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession([FakeResponse(text=load_fixture("kac_departures.xml"))])
    client = KrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    run = client.debug_departures(
        airport_code="GMP",
        searchday=date(2026, 4, 30),
        from_time="0600",
        to_time="1200",
    )

    assert isinstance(run, DebugRun)
    assert run.function == "departures"
    assert run.error is None
    assert run.request["params"]["airport_code"] == "GMP"
    assert run.response["body"][0]["flightId"] == "KE1201"

    dumped = jsonable(run)
    assert dumped["processed"][0]["provider"] == "kac"
    assert dumped["processed"][0]["scheduled_at"] == "2026-04-30T06:00:00+09:00"


def test_debug_rejects_unknown_function_without_calling_network() -> None:
    client = KrairportClient(kac_service_key="KAC_KEY", iiac_service_key="IIAC_KEY")

    run = client.debug("from_env")

    assert run.error is not None
    assert run.error["type"] == "ValueError"
    assert run.processed is None


def test_redact_sensitive_masks_nested_auth_values() -> None:
    value = {
        "serviceKey": "secret",
        "nested": [{"Authorization": "Bearer token"}],
        "safe": "kept",
    }

    assert redact_sensitive(value) == {
        "serviceKey": "<REDACTED>",
        "nested": [{"Authorization": "<REDACTED>"}],
        "safe": "kept",
    }
