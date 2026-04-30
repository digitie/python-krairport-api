from __future__ import annotations

from datetime import date

from pykrairport.client import KrairportClient
from tests.conftest import FakeResponse, FakeSession


def _json_response(items):  # type: ignore[no-untyped-def]
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "body": {"items": {"item": items}},
        }
    }


def test_unified_client_routes_kac_departures(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession([FakeResponse(text=load_fixture("kac_departures.xml"))])
    client = KrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    rows = client.departures(
        airport_code="GMP",
        searchday=date(2026, 4, 30),
        from_time="0600",
        to_time="1200",
    )

    assert session.calls[0].url.endswith("/getDepFlightStatusList")
    assert session.calls[0].params["airport_code"] == "GMP"
    assert rows[0].provider == "kac"


def test_unified_client_routes_iiac_arrivals() -> None:
    payload = _json_response(
        {
            "flightId": "KE5942",
            "scheduleDateTime": "202604300600",
            "estimatedDateTime": "202604300610",
            "codeshare": "N",
        }
    )
    session = FakeSession([FakeResponse(json_data=payload)])
    client = KrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    rows = client.arrivals(
        airport_code="ICN",
        searchday="20260430",
        use_detailed=True,
    )

    assert session.calls[0].url.endswith("/getPassengerArrivalsDeOdp")
    assert session.calls[0].params["type"] == "json"
    assert rows[0].provider == "iiac"


def test_unified_client_routes_iiac_parking_status() -> None:
    payload = _json_response(
        {
            "terminal": "T2",
            "parking": "장기주차장",
            "parkingIstay": "10",
            "parkingFullSpace": "100",
        }
    )
    session = FakeSession([FakeResponse(json_data=payload)])
    client = KrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    rows = client.parking_status()

    assert session.calls[0].url.endswith("/getTrackingParking")
    assert rows[0].terminal == "T2"
    assert rows[0].occupied == 10


def test_unified_client_routes_remaining_methods(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession(
        [
            FakeResponse(text=load_fixture("kac_arrivals_single.xml")),
            FakeResponse(text=load_fixture("kac_aircraft.xml")),
            FakeResponse(text=load_fixture("kac_parking_fee.xml")),
            FakeResponse(
                json_data=_json_response(
                    {
                        "terno": "T1",
                        "entrygate": "A",
                        "kor": "1",
                        "foreigner": "2",
                    }
                )
            ),
            FakeResponse(
                json_data=_json_response(
                    {
                        "adate": "20260430",
                        "atime": "06_07",
                        "t1eg1": "1",
                        "t1eg2": "2",
                        "t1dgsum1": "3",
                    }
                )
            ),
        ]
    )
    client = KrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    assert client.arrivals(airport_code="GMP")[0].provider == "kac"
    assert client.aircraft_assignments(airport_code="CJU")[0].aircraft_registration == "HL8000"
    assert client.parking_fees(airport_code="GMP")[0].small_basic_fee == 1000
    assert client.arrival_congestion(terminal="T1")[0].korean_count == 1
    assert client.passenger_forecast()[0].t1_departure_total == 3
