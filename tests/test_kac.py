from __future__ import annotations

from datetime import datetime

import pytest

from pykrairport.exceptions import KrairportParseError, UnsupportedAirportError
from pykrairport.providers.kac import KacClient
from tests.conftest import FakeResponse, FakeSession


def test_departures_parse_types_and_request_params(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession([FakeResponse(text=load_fixture("kac_departures.xml"))])
    client = KacClient("KAC_KEY", session=session, retries=0)

    rows = client.departures(
        airport_code="GMP",
        searchday="20260430",
        from_time="0600",
        to_time="1200",
        flight_id="KE1201",
    )

    assert session.calls[0].url.endswith("/getDepFlightStatusList")
    assert session.calls[0].params["serviceKey"] == "KAC_KEY"
    assert session.calls[0].params["airport_code"] == "GMP"
    assert session.calls[0].params["flight_id"] == "KE1201"
    assert "type" not in session.calls[0].params

    first = rows[0]
    assert first.provider == "kac"
    assert first.direction == "departure"
    assert first.flight_id == "KE1201"
    assert first.arrival_airport_code == "CJU"
    assert isinstance(first.scheduled_at, datetime)
    assert first.scheduled_at.isoformat() == "2026-04-30T06:00:00+09:00"
    assert first.codeshare is False
    assert rows[1].codeshare is True


def test_arrivals_normalize_single_item(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession([FakeResponse(text=load_fixture("kac_arrivals_single.xml"))])
    client = KacClient("KAC_KEY", session=session, retries=0)

    rows = client.arrivals(airport_code="GMP", searchday="20260430")

    assert len(rows) == 1
    assert rows[0].direction == "arrival"
    assert rows[0].departure_airport_code == "PUS"
    assert rows[0].status_korean == "도착"


def test_kac_rejects_icn() -> None:
    client = KacClient("KAC_KEY", session=FakeSession([]), retries=0)

    with pytest.raises(UnsupportedAirportError):
        client.departures(airport_code="ICN")


def test_aircraft_assignments(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession([FakeResponse(text=load_fixture("kac_aircraft.xml"))])
    client = KacClient("KAC_KEY", session=session, retries=0)

    rows = client.aircraft_assignments(
        airport_code="CJU",
        sch_st_time="202604300600",
        sch_ed_time="202604301200",
    )

    assert session.calls[0].params["schAirCode"] == "CJU"
    assert rows[0].flight_id == "KE1201"
    assert rows[0].aircraft_registration == "HL8000"
    assert rows[0].aircraft_type == "B738"
    assert rows[0].gate == "12"


def test_parking_fees_convert_amounts(load_fixture) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession([FakeResponse(text=load_fixture("kac_parking_fee.xml"))])
    client = KacClient("KAC_KEY", session=session, retries=0)

    rows = client.parking_fees(airport_code="GMP")

    assert session.calls[0].url.endswith("/parkingfee")
    assert session.calls[0].params["schAirportCode"] == "GMP"
    fee = rows[0]
    assert fee.parking_name == "국내선 제1주차장"
    assert fee.small_basic_minutes == 30
    assert fee.small_basic_fee == 1000
    assert fee.large_daily_max_fee == 40000


def test_bad_kac_numeric_value_becomes_parse_error() -> None:
    xml = """<response><header><resultCode>00</resultCode></header><body><items><item>
        <airportCode>GMP</airportCode><parkingBasicM>bad</parkingBasicM>
    </item></items></body></response>"""
    client = KacClient("KAC_KEY", session=FakeSession([FakeResponse(text=xml)]), retries=0)

    with pytest.raises(KrairportParseError):
        client.parking_fees(airport_code="GMP")


def test_airport_codes() -> None:
    xml = """<response><header><resultCode>00</resultCode></header><body><items><item>
        <cityCode>GMP</cityCode><cityKor>김포</cityKor><cityEng>Gimpo</cityEng>
    </item></items></body></response>"""
    session = FakeSession([FakeResponse(text=xml)])
    client = KacClient("KAC_KEY", session=session, retries=0)

    rows = client.airport_codes(code="GMP")

    assert session.calls[0].url.endswith("/getAirportCodeList")
    assert session.calls[0].params["cityCode"] == "GMP"
    assert rows[0].code == "GMP"
    assert rows[0].english_name == "Gimpo"
    assert rows[0].icao_code == "RKSS"
    assert rows[0].coordinate is not None
    assert rows[0].coordinate.latitude == 37.5583


def test_flight_schedules() -> None:
    xml = """<response><header><resultCode>00</resultCode></header><body><items><item>
        <domesticNum>KE1201</domesticNum><airlineKorean>대한항공</airlineKorean>
        <startcity>GMP</startcity><arrivalcity>CJU</arrivalcity>
        <domesticStartTime>0600</domesticStartTime>
        <domesticStdate>20260401</domesticStdate><domesticEddate>20261030</domesticEddate>
        <domesticMon>Y</domesticMon>
    </item></items></body></response>"""
    session = FakeSession([FakeResponse(text=xml)])
    client = KacClient("KAC_KEY", session=session, retries=0)

    rows = client.flight_schedules(
        direction="departure",
        airport_code="GMP",
        counterpart_airport_code="CJU",
    )

    assert session.calls[0].url.endswith("/getDflightScheduleList")
    assert session.calls[0].params["schDeptCityCode"] == "GMP"
    assert rows[0].flight_id == "KE1201"
    assert rows[0].scheduled_time == "0600"


def test_kac_parking_status_facilities_buses_and_taxi() -> None:
    parking_xml = """<response><header><resultCode>00</resultCode></header><body><items><item>
        <parkingAirportCode>GMP</parkingAirportCode><parkingAirportName>국내선</parkingAirportName>
        <parkingOccupiedSpace>10</parkingOccupiedSpace><parkingTotalSpace>100</parkingTotalSpace>
        <sysGetdate>202604301200</sysGetdate>
    </item></items></body></response>"""
    facility_xml = """<response><header><resultCode>00</resultCode></header><body><items><item>
        <apcd>GMP</apcd><facilityNm>안내데스크</facilityNm><floor>1F</floor>
        <address>서울특별시 강서구 하늘길 112</address>
    </item></items></body></response>"""
    bus_xml = """<response><header><resultCode>00</resultCode></header><body><items><item>
        <busnumber>6000</busnumber><adultfare>15000</adultfare><routeinfo>서울</routeinfo>
    </item></items></body></response>"""
    taxi_xml = """<response><header><resultCode>00</resultCode></header><body><items><item>
        <stand>1</stand><seoultaxicnt>2</seoultaxicnt><datetm>202604301200</datetm>
    </item></items></body></response>"""
    session = FakeSession(
        [
            FakeResponse(text=parking_xml),
            FakeResponse(text=facility_xml),
            FakeResponse(text=bus_xml),
            FakeResponse(text=taxi_xml),
        ]
    )
    client = KacClient("KAC_KEY", session=session, retries=0)

    assert client.parking_status(airport_code="GMP")[0].occupied == 10
    facility = client.airport_facilities(airport_code="GMP")[0]
    assert facility.name == "안내데스크"
    assert facility.address is not None
    assert facility.address.display_address == "서울특별시 강서구 하늘길 112"
    assert client.airport_buses(airport_code="GMP")[0].adult_fare == 15000
    assert client.jeju_taxi_wait()[0].seoul_count == 2


def test_kac_raw_items_and_path_validation() -> None:
    xml = """<response><header><resultCode>00</resultCode></header><body><items><item>
        <foo>bar</foo>
    </item></items></body></response>"""
    session = FakeSession([FakeResponse(text=xml)])
    client = KacClient("KAC_KEY", session=session, retries=0)

    rows = client.raw_items("noise", "getNoise", {"pageNo": 1})

    assert session.calls[0].url.endswith("/noise/getNoise")
    assert rows[0]["foo"] == "bar"
    with pytest.raises(ValueError):
        client.raw_items("../noise", "getNoise")
