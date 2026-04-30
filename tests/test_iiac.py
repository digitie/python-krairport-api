from __future__ import annotations

from datetime import datetime

import pytest

from pykrairport.exceptions import UnsupportedAirportError
from pykrairport.providers.iiac import IiacClient
from tests.conftest import FakeResponse, FakeSession


def _json_response(items):  # type: ignore[no-untyped-def]
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "body": {"items": {"item": items}, "pageNo": 1, "numOfRows": 10, "totalCount": 1},
        }
    }


def test_detailed_arrivals_parse_types_and_request_params() -> None:
    payload = _json_response(
        {
            "airline": "대한항공",
            "airport": "HAN",
            "flightId": "KE5942",
            "f_id": "2023032800000004944564",
            "scheduleDateTime": "202604300600",
            "estimatedDateTime": "2.02604300610E+11",
            "remarkKor": "도착",
            "remarkEng": "Arrived",
            "terminalid": "T2",
            "gatenumber": "251",
            "codeshare": "Y",
        }
    )
    session = FakeSession([FakeResponse(json_data=payload)])
    client = IiacClient("IIAC_KEY", session=session, retries=0)

    rows = client.arrivals(
        airport_code="ICN",
        searchday="20260430",
        from_time="0000",
        to_time="2400",
        flight_id="KE5942",
        detailed=True,
    )

    assert session.calls[0].url.endswith("/getPassengerArrivalsDeOdp")
    assert session.calls[0].params["type"] == "json"
    assert session.calls[0].params["serviceKey"] == "IIAC_KEY"
    assert session.calls[0].params["searchday"] == "20260430"
    assert "airport_code" not in session.calls[0].params

    row = rows[0]
    assert row.provider == "iiac"
    assert row.airport_code == "ICN"
    assert row.direction == "arrival"
    assert row.flight_id == "KE5942"
    assert row.flight_unique_id == "2023032800000004944564"
    assert row.terminal == "T2"
    assert row.codeshare is True
    assert isinstance(row.estimated_at, datetime)
    assert row.estimated_at.isoformat() == "2026-04-30T06:10:00+09:00"


def test_today_departures_do_not_send_searchday() -> None:
    payload = _json_response(
        [
            {
                "airline": "아시아나항공",
                "airport": "NRT",
                "flightId": "OZ102",
                "scheduleDateTime": "202604301100",
                "codeshare": "N",
            }
        ]
    )
    session = FakeSession([FakeResponse(json_data=payload)])
    client = IiacClient("IIAC_KEY", session=session, retries=0)

    rows = client.departures(airport_code="ICN", searchday="20260430", detailed=False)

    assert session.calls[0].url.endswith("/getPassengerDeparturesOdp")
    assert "searchday" not in session.calls[0].params
    assert rows[0].direction == "departure"
    assert rows[0].codeshare is False


def test_iiac_rejects_non_icn() -> None:
    client = IiacClient("IIAC_KEY", session=FakeSession([]), retries=0)

    with pytest.raises(UnsupportedAirportError):
        client.parking_status(airport_code="GMP")


def test_parking_status_converts_counts() -> None:
    payload = _json_response(
        {
            "terminal": "T1",
            "parking": "단기주차장 지하1층",
            "parkingIstay": "1234",
            "parkingFullSpace": "2000",
            "datetm": "202604301230",
        }
    )
    client = IiacClient(
        "IIAC_KEY",
        session=FakeSession([FakeResponse(json_data=payload)]),
        retries=0,
    )

    rows = client.parking_status()

    assert rows[0].airport_code == "ICN"
    assert rows[0].occupied == 1234
    assert rows[0].capacity == 2000
    assert rows[0].updated_at is not None


def test_arrival_congestion_converts_counts() -> None:
    payload = _json_response(
        {
            "terno": "T1",
            "entrygate": "A",
            "flightid": "KE123",
            "airport": "LAX",
            "gatenumber": "11",
            "scheduletime": "202604301300",
            "estimatedtime": "202604301310",
            "kor": "100",
            "foreigner": "250",
        }
    )
    client = IiacClient(
        "IIAC_KEY",
        session=FakeSession([FakeResponse(json_data=payload)]),
        retries=0,
    )

    rows = client.arrival_congestion(terminal="T1")

    assert rows[0].terminal == "T1"
    assert rows[0].entry_gate == "A"
    assert rows[0].korean_count == 100
    assert rows[0].foreign_count == 250


def test_passenger_forecast_converts_counts() -> None:
    payload = _json_response(
        {
            "adate": "20260430",
            "atime": "06_07",
            "t1eg1": "100",
            "t1eg2": "200",
            "t1dgsum1": "300",
            "t2egsum1": "400",
            "t2dgsum1": "500",
        }
    )
    client = IiacClient(
        "IIAC_KEY",
        session=FakeSession([FakeResponse(json_data=payload)]),
        retries=0,
    )

    rows = client.passenger_forecast(selectdate=1)

    assert rows[0].display_date == "20260430"
    assert rows[0].time_range == "06_07"
    assert rows[0].t1_arrival_east == 100
    assert rows[0].t2_departure_total == 500


def test_taxi_bus_weather_schedule_destination_and_facility() -> None:
    session = FakeSession(
        [
            FakeResponse(
                json_data=_json_response(
                    {
                        "terno": "P01",
                        "seoultaxicnt": "3",
                        "incheontaxicnt": "4",
                        "datetm": "202604301200",
                    }
                )
            ),
            FakeResponse(
                json_data=_json_response(
                    {
                        "area": "1",
                        "busnumber": "6100",
                        "adultfare": "18000",
                        "routeinfo": "서울",
                    }
                )
            ),
            FakeResponse(
                json_data=_json_response(
                    {
                        "flightId": "KE1",
                        "airport": "NRT",
                        "weather": "맑음",
                        "temperature": "20",
                        "humidity": "50",
                    }
                )
            ),
            FakeResponse(
                json_data=_json_response(
                    {
                        "flightId": "KE1",
                        "airlineNm": "대한항공",
                        "airport": "NRT",
                        "scheduleTime": "0900",
                        "week": "1234567",
                    }
                )
            ),
            FakeResponse(
                json_data=_json_response(
                    {
                        "airportCode": "NRT",
                        "airportName": "Narita",
                        "cityCode": "TYO",
                        "cityName": "Tokyo",
                        "countryName": "Japan",
                    }
                )
            ),
            FakeResponse(
                json_data=_json_response(
                    {
                        "facility_nm": "편의점",
                        "terminal": "T1",
                        "floor": "1F",
                    }
                )
            ),
        ]
    )
    client = IiacClient("IIAC_KEY", session=session, retries=0)

    assert client.taxi_status(terminal="P01")[0].seoul_count == 3
    assert client.bus_routes(area="1")[0].adult_fare == 18000
    assert client.world_weather(direction="arrival")[0].temperature == 20
    assert client.flight_schedules(direction="arrival")[0].flight_id == "KE1"
    assert client.service_destinations()[0].city_code == "TYO"
    assert client.facilities()[0].name == "편의점"

    assert session.calls[0].url.endswith("/getTaxiStatus")
    assert session.calls[1].url.endswith("/getBusInfo")
    assert session.calls[2].url.endswith("/getPassengerArrivalsWorldWeather")
    assert session.calls[3].url.endswith("/getPaxFltSchedArrivals")
    assert session.calls[4].url.endswith("/getServiceDestinationInfo")
    assert session.calls[5].url.endswith("/getFacilityKR")


def test_iiac_raw_items_and_path_validation() -> None:
    session = FakeSession(
        [
            FakeResponse(json_data=_json_response({"foo": "bar"})),
            FakeResponse(json_data=_json_response({"flightId": "KE1"})),
        ]
    )
    client = IiacClient("IIAC_KEY", session=session, retries=0)

    rows = client.raw_items("ShtbusInfo", "getShtbusInfo", {"pageNo": 1})
    changed_url_rows = client.raw_items(
        "FlightClosingInfoSpot",
        "getFlightClosingInfoSpot",
        {"pageNo": 1},
    )

    assert session.calls[0].url.endswith("/ShtbusInfo/getShtbusInfo")
    assert session.calls[0].params["type"] == "json"
    assert session.calls[1].url.endswith("/FlightClosingInfoSpot/getFlightClosingInfoSpot")
    assert rows[0]["foo"] == "bar"
    assert changed_url_rows[0]["flightId"] == "KE1"
    with pytest.raises(ValueError):
        client.raw_items("http://example.com", "getShtbusInfo")
