from __future__ import annotations

from datetime import date

import pytest
from kraddr.base import PlaceCoordinate

from krairport.client import AsyncKrairportClient, KrairportClient
from tests.conftest import AsyncFakeSession, FakeResponse, FakeSession


def _json_response(items):  # type: ignore[no-untyped-def]
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "body": {"items": {"item": items}},
        }
    }


def _xml_response(item: str) -> str:
    return (
        "<response><header><resultCode>00</resultCode></header>"
        f"<body><items><item>{item}</item></items></body></response>"
    )


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


def test_unified_client_routes_new_missing_api_methods() -> None:
    def response(item):  # type: ignore[no-untyped-def]
        return FakeResponse(json_data=_json_response(item))

    session = FakeSession(
        [
            response({"flightId": "KE1", "scheduleTime": "0900"}),
            response({"facility_nm": "편의점"}),
            response({"busnumber": "6100", "adultfare": "18000"}),
            response({"seoultaxicnt": "3"}),
            response({"airportCode": "NRT", "cityCode": "TYO"}),
        ]
    )
    client = KrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    assert client.flight_schedules(airport_code="ICN", direction="arrival")[0].flight_id == "KE1"
    assert client.airport_facilities(airport_code="ICN")[0].name == "편의점"
    assert client.bus_routes(airport_code="ICN")[0].bus_number == "6100"
    assert client.taxi_status(airport_code="ICN")[0].seoul_count == 3
    assert client.service_destinations()[0].city_code == "TYO"


def test_unified_client_raw_items(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession(
        [
            FakeResponse(text=load_fixture("kac_arrivals_single.xml")),
            FakeResponse(json_data=_json_response({"foo": "bar"})),
        ]
    )
    client = KrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    assert client.kac_raw_items("StatusOfFlights", "getArrFlightStatusList")[0]["flightId"]
    assert client.iiac_raw_items("ShtbusInfo", "getShtbusInfo")[0]["foo"] == "bar"


def test_unified_client_exposes_airport_metadata_helpers() -> None:
    client = KrairportClient(kac_service_key="KAC_KEY", iiac_service_key="IIAC_KEY")

    assert client.airport_metadata("icn").provider == "iiac"
    assert client.airports(provider="kac", active=False)[0].code == "MPK"
    coordinate = PlaceCoordinate.from_values("37.56", "126.79")
    assert client.nearest_airport(coordinate).code == "GMP"


def test_client_from_env_reads_local_dotenv(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KAC_SERVICE_KEY", raising=False)
    monkeypatch.delenv("IIAC_SERVICE_KEY", raising=False)
    (tmp_path / ".env").write_text(
        'KAC_SERVICE_KEY="  KAC_FROM_FILE  "\nIIAC_SERVICE_KEY= IIAC_FROM_FILE \n',
        encoding="utf-8",
    )

    client = KrairportClient.from_env()

    assert client.config.kac_service_key == "KAC_FROM_FILE"
    assert client.config.iiac_service_key == "IIAC_FROM_FILE"


def test_unified_client_iter_pages() -> None:
    client = KrairportClient(kac_service_key="KAC_KEY", iiac_service_key="IIAC_KEY")
    calls: list[int] = []

    def fetch_page(*, page_no: int, num_of_rows: int) -> list[int]:
        calls.append(page_no)
        return [page_no] * num_of_rows if page_no == 1 else [page_no]

    pages = list(client.iter_pages(fetch_page, num_of_rows=2))

    assert calls == [1, 2]
    assert len(pages) == 2
    assert pages[0].items == [1, 1]
    assert pages[1].items == [2]


@pytest.mark.asyncio
async def test_async_unified_client_routes_iiac_arrivals() -> None:
    payload = _json_response(
        {
            "flightId": "KE5942",
            "scheduleDateTime": "202604300600",
            "estimatedDateTime": "202604300610",
            "codeshare": "N",
        }
    )
    session = AsyncFakeSession([FakeResponse(json_data=payload)])
    client = AsyncKrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    rows = await client.arrivals(
        airport_code="ICN",
        searchday="20260430",
        use_detailed=True,
    )

    assert session.calls[0].url.endswith("/getPassengerArrivalsDeOdp")
    assert rows[0].provider == "iiac"


@pytest.mark.asyncio
async def test_async_unified_client_routes_many_methods(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = AsyncFakeSession(
        [
            FakeResponse(text=load_fixture("kac_departures.xml")),
            FakeResponse(text=load_fixture("kac_aircraft.xml")),
            FakeResponse(text=load_fixture("kac_parking_fee.xml")),
            FakeResponse(
                text=_xml_response(
                    "<parkingAirportCode>GMP</parkingAirportCode><parkingAirportName>GMP</parkingAirportName>"
                    "<parkingOccupiedSpace>10</parkingOccupiedSpace><parkingTotalSpace>100</parkingTotalSpace>"
                )
            ),
            FakeResponse(json_data=_json_response({"terminal": "T1", "parkingIstay": "1"})),
            FakeResponse(json_data=_json_response({"terno": "T1", "entrygate": "A", "kor": "1"})),
            FakeResponse(json_data=_json_response({"adate": "20260430", "atime": "06_07"})),
            FakeResponse(json_data=_json_response({"flightId": "KE1", "scheduleTime": "0900"})),
            FakeResponse(json_data=_json_response({"facility_nm": "Clinic"})),
            FakeResponse(json_data=_json_response({"busnumber": "6100", "adultfare": "18000"})),
            FakeResponse(json_data=_json_response({"seoultaxicnt": "3"})),
            FakeResponse(
                json_data=_json_response(
                    {"flightId": "KE1", "airport": "NRT", "temperature": "20"}
                )
            ),
            FakeResponse(json_data=_json_response({"airportCode": "NRT", "cityCode": "TYO"})),
            FakeResponse(text=_xml_response("<facilityNm>Info</facilityNm>")),
            FakeResponse(text=_xml_response("<busnumber>6000</busnumber><adultfare>15000</adultfare>")),
            FakeResponse(text=_xml_response("<stand>1</stand><seoultaxicnt>2</seoultaxicnt>")),
            FakeResponse(text=load_fixture("kac_arrivals_single.xml")),
            FakeResponse(json_data=_json_response({"foo": "bar"})),
        ]
    )
    client = AsyncKrairportClient(
        kac_service_key="KAC_KEY",
        iiac_service_key="IIAC_KEY",
        session=session,
        retries=0,
    )

    assert (await client.departures(airport_code="GMP"))[0].provider == "kac"
    assert (await client.aircraft_assignments(airport_code="CJU"))[0].flight_id
    assert (await client.parking_fees(airport_code="GMP"))[0].small_basic_fee == 1000
    assert (await client.parking_status(airport_code="GMP"))[0].occupied == 10
    assert (await client.parking_status())[0].occupied == 1
    assert (await client.arrival_congestion())[0].entry_gate == "A"
    assert (await client.passenger_forecast())[0].display_date == "20260430"
    assert (await client.flight_schedules(airport_code="ICN", direction="arrival"))[0].flight_id
    assert (await client.airport_facilities(airport_code="ICN"))[0].name == "Clinic"
    assert (await client.bus_routes(airport_code="ICN"))[0].bus_number == "6100"
    assert (await client.taxi_status(airport_code="ICN"))[0].seoul_count == 3
    assert (await client.world_weather(direction="arrival"))[0].temperature == 20
    assert (await client.service_destinations())[0].city_code == "TYO"
    assert (await client.airport_facilities(airport_code="GMP"))[0].name == "Info"
    assert (await client.bus_routes(airport_code="GMP"))[0].bus_number == "6000"
    assert (await client.taxi_status(airport_code="CJU"))[0].seoul_count == 2
    assert (await client.kac_raw_items("StatusOfFlights", "getArrFlightStatusList"))[0]["flightId"]
    assert (await client.iiac_raw_items("ShtbusInfo", "getShtbusInfo"))[0]["foo"] == "bar"

    async with client:
        assert client.airport_metadata("ICN").code == "ICN"


@pytest.mark.asyncio
async def test_async_iter_pages() -> None:
    client = AsyncKrairportClient(kac_service_key="KAC_KEY", iiac_service_key="IIAC_KEY")

    async def fetch_page(*, page_no: int, num_of_rows: int) -> list[int]:
        return [page_no] * num_of_rows if page_no == 1 else []

    pages = [
        page
        async for page in client.iter_pages(fetch_page, num_of_rows=2, max_pages=2)
    ]

    assert [page.page for page in pages] == [1, 2]
    assert pages[0].items == [1, 1]
