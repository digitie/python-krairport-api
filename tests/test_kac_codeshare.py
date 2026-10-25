"""공동운항의 개별 편명과 중복 페이지 검증을 실제 공개 행으로 고정한다."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest

from krairport import KrairportClient
from krairport.exceptions import KrairportParseError
from tests.conftest import FakeResponse, FakeSession

FIXTURE = Path(__file__).parent / "fixtures" / "kac_gmp_codeshare_20261025.json"


def _response(
    rows: list[dict[str, Any]], *, page: int = 1, size: int = 100, total: int | None = None,
) -> FakeResponse:
    root = ET.Element("response")
    ET.SubElement(ET.SubElement(root, "header"), "resultCode").text = "00"
    body = ET.SubElement(root, "body")
    for name, value in {"pageNo": page, "numOfRows": size,
                        "totalCount": len(rows) if total is None else total}.items():
        ET.SubElement(body, name).text = str(value)
    items = ET.SubElement(body, "items")
    for row in rows:
        item = ET.SubElement(items, "item")
        for name, value in row.items():
            ET.SubElement(item, name).text = str(value) if value is not None else None
    return FakeResponse(text=ET.tostring(root, encoding="unicode"))


def _pair() -> list[dict[str, Any]]:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return deepcopy(rows[1:3])


async def test_captured_public_page_preserves_all_marketing_flights() -> None:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # 원본 첫 페이지의 행은 보존하고, 부분 집합 재생용 총건수만 100으로 구성한다.
    session = FakeSession([_response(rows), _response([])])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        flights = await client.kac.flight_status(airport_code="GMP", searchday="20261025")

    assert len(flights) == len(rows) == 100
    assert [flight.flight_id for flight in flights] == [row["flightid"] for row in rows]
    assert [flight.flight_unique_id for flight in flights] == [row["fid"] for row in rows]
    assert [flight.master_flight_id for flight in flights] == [
        row["masterflightid"] or None for row in rows
    ]
    assert flights[1].flight_id == "LJ6301"
    assert flights[2].flight_id == "KE5153"
    assert flights[1].flight_unique_id == flights[2].flight_unique_id == "0000000000000013491693"
    assert flights[1].master_flight_id == flights[2].master_flight_id == "LJ6301"
    assert flights[1].scheduled_at.isoformat() == "2026-10-25T06:05:00+09:00"
    assert all(flight.raw == row for flight, row in zip(flights, rows, strict=True))
    assert len(session.calls) == 2


@pytest.mark.parametrize("direction", ["departure", "arrival"])
async def test_codeshare_can_cross_pages_without_collapsing_marketing_ids(direction: str) -> None:
    pair = _pair()
    if direction == "arrival":
        for row in pair:
            row["io"] = "I"
            row["depAirportCode"], row["arrvAirportCode"] = "CJU", "GMP"
    responses = [_response([row], page=index, size=1, total=2)
                 for index, row in enumerate(pair, start=1)]
    responses.insert(0 if direction == "arrival" else len(responses), _response([]))
    session = FakeSession(responses)
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        flights = await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert [flight.flight_id for flight in flights] == ["LJ6301", "KE5153"]
    assert all(str(flight.direction) == direction for flight in flights)
    assert [call.params["pageNo"] for call in session.calls] == (
        [1, 1, 2] if direction == "arrival" else [1, 2, 1]
    )


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "codeshare", "N"), (0, "codeshare", ""),
        (1, "codeshare", "N"), (1, "codeshare", ""),
        (0, "masterflightid", ""), (1, "masterflightid", ""),
        (1, "masterflightid", "private-conflicting-master"),
        (1, "scheduledatetime", "202610250610"),
        (1, "scheduledatetime", "202610260605"),
        (1, "depAirportCode", "PUS"), (1, "arrvAirportCode", "PUS"),
        (0, "depAirportCode", ""), (0, "arrvAirportCode", ""),
        (1, "depAirportCode", ""), (1, "arrvAirportCode", ""),
        (0, "searchday", "20261026"), (0, "io", "I"),
        (1, "searchday", "20261026"), (1, "io", "I"),
    ],
)
async def test_shared_fid_requires_explicit_consistent_codeshare(
    index: int, field: str, value: str,
) -> None:
    pair = _pair()
    pair[index][field] = value
    session = FakeSession([_response(pair), _response([])])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError) as caught:
            await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert "private-conflicting-master" not in str(caught.value)
    assert len(session.calls) == 1


async def test_shared_fid_does_not_require_identical_generation_timestamps() -> None:
    pair = _pair()
    pair[1]["fgenTime"] = "20261025203610"
    session = FakeSession([_response(pair), _response([])])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        flights = await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert len(flights) == 2
    assert flights[0].raw["fgenTime"] != flights[1].raw["fgenTime"]


async def test_codeshare_keeps_next_day_kst_midnight() -> None:
    pair = _pair()
    for row in pair:
        row["scheduledatetime"] = "202610260000"
    session = FakeSession([_response(pair), _response([])])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        flights = await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert all(flight.scheduled_at.isoformat() == "2026-10-26T00:00:00+09:00"
               for flight in flights)


async def test_codeshare_allows_absent_optional_raw_day_and_io() -> None:
    pair = _pair()
    for row in pair:
        row.pop("searchday")
        row.pop("io")
    session = FakeSession([_response(pair), _response([])])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        flights = await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert len(flights) == 2


@pytest.mark.parametrize(
    "direction,departure,arrival",
    [
        ("departure", "CJU", "PUS"), ("departure", "CJU", "GMP"),
        ("arrival", "PUS", "CJU"), ("arrival", "GMP", "CJU"),
    ],
)
async def test_shared_fid_route_must_match_requested_airport_and_direction(
    direction: str, departure: str, arrival: str,
) -> None:
    pair = _pair()
    for row in pair:
        row["io"] = "O" if direction == "departure" else "I"
        row["depAirportCode"] = departure
        row["arrvAirportCode"] = arrival
    responses = [_response(pair)]
    if direction == "arrival":
        responses.insert(0, _response([]))
    session = FakeSession(responses)
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError, match="공동운항"):
            await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert len(session.calls) == (1 if direction == "departure" else 2)


async def test_singleton_route_policy_is_unchanged() -> None:
    row = _pair()[0]
    row["depAirportCode"], row["arrvAirportCode"] = "CJU", "PUS"
    session = FakeSession([_response([row]), _response([])])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        flights = await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert len(flights) == 1
    assert flights[0].departure_airport_code == "CJU"


@pytest.mark.parametrize("changed_schedule", [False, True])
@pytest.mark.parametrize("across_pages", [False, True])
async def test_same_fid_and_marketing_id_remain_duplicates(
    changed_schedule: bool, across_pages: bool,
) -> None:
    first = _pair()[0]
    second = deepcopy(first)
    if changed_schedule:
        second["scheduledatetime"] = "202610250610"
    responses = (
        [_response([first], size=1, total=2), _response([second], page=2, size=1, total=2)]
        if across_pages else [_response([first, second])]
    )
    session = FakeSession(responses)
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError, match="중복"):
            await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert len(session.calls) == (2 if across_pages else 1)


async def test_overlapping_codeshare_pages_still_fail() -> None:
    first, marketing = _pair()
    third = deepcopy(marketing)
    third["flightid"] = "KE5154"
    session = FakeSession([
        _response([first, marketing], size=2, total=4),
        _response([third, marketing], page=2, size=2, total=4),
    ])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError, match="중복"):
            await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert len(session.calls) == 2


async def test_same_fid_in_opposite_direction_has_an_independent_identity() -> None:
    row = _pair()[0]
    row["codeshare"] = "N"
    arrival = deepcopy(row)
    arrival["io"] = "I"
    session = FakeSession([_response([row]), _response([arrival])])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        flights = await client.kac.flight_status(airport_code="GMP", searchday="20261025")
    assert [str(flight.direction) for flight in flights] == ["departure", "arrival"]


@pytest.mark.parametrize("changed_schedule", [False, True])
async def test_no_fid_keeps_existing_flight_and_schedule_fallback(changed_schedule: bool) -> None:
    first = _pair()[0]
    first.pop("fid")
    second = deepcopy(first)
    if changed_schedule:
        second["scheduledatetime"] = "202610250610"
    session = FakeSession([_response([first, second]), _response([])])
    async with KrairportClient(kac_service_key="offline-key", session=session, retries=0) as client:
        if changed_schedule:
            flights = await client.kac.flight_status(airport_code="GMP", searchday="20261025")
            assert len(flights) == 2
            assert all(flight.flight_unique_id is None for flight in flights)
        else:
            with pytest.raises(KrairportParseError, match="중복"):
                await client.kac.flight_status(airport_code="GMP", searchday="20261025")
