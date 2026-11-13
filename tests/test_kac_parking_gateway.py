"""공식 15158681의 주차 전용 GW 요청·원문·완결성·인증 실패를 오프라인 재생한다."""

import json
from datetime import timedelta
from pathlib import Path
from xml.etree import ElementTree

import pytest

from krairport import (
    KrairportAuthError,
    KrairportClient,
    KrairportParseError,
    api_catalog,
    parse_parking_snapshot_values,
)
from krairport.providers.kac import KacClient
from tests.conftest import AsyncFakeSession, FakeResponse

CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures/kac_parking_realtime_contract.json").read_text()
)


def response(page=1, names=("국내선 제1주차장",), total=1, size=100, clock="18:16:00"):
    # 공식 응답 필드 기반 합성 행이다. 실사용 KAC 응답/등록 성공으로 주장하지 않는다.
    items = "".join(
        f"<item><parkingAirportCodeName>{name}</parkingAirportCodeName>"
        "<parkingFullSpace>640</parkingFullSpace><parkingIstay>0</parkingIstay>"
        f"<parkingGetdate>2026-11-13</parkingGetdate><parkingGettime>{clock}</parkingGettime>"
        "<aprEng>Gimpo</aprEng><aprKor>김포</aprKor><parkingIincnt>1</parkingIincnt>"
        "<parkingIoutcnt>2</parkingIoutcnt></item>"
        for name in names
    )
    return FakeResponse(
        text=(
            "<response><header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg>"
            f"</header><body><totalCount>{total}</totalCount><pageNo>{page}</pageNo>"
            f"<numOfRows>{size}</numOfRows><items>{items}</items></body></response>"
        )
    )


def assert_official_request(call):
    assert call.url == CONTRACT["endpoint"]
    allowed = {parameter["name"] for parameter in CONTRACT["parameters"]}
    required = {parameter["name"] for parameter in CONTRACT["parameters"] if parameter["required"]}
    assert required <= set(call.params) <= allowed
    assert call.params["type"] == "xml"


@pytest.mark.parametrize("realtime", [False, True])
async def test_parking_status_uses_official_gw_and_preserves_source_fields(realtime):
    session = AsyncFakeSession([response(page=2, size=1)])
    client = KacClient("fixture", session=session, retries=0)
    rows = await client.parking_status(
        airport_code="GMP", page_no=2, num_of_rows=1, realtime=realtime
    )
    assert_official_request(session.calls[0])
    assert session.calls[0].params["schAirportCode"] == "GMP"
    assert session.calls[0].params["pageNo"] == 2 and session.calls[0].params["numOfRows"] == 1
    assert rows[0].parking_area == "국내선 제1주차장"
    assert rows[0].occupied == 0 and rows[0].capacity == 640
    assert rows[0].updated_at.isoformat() == "2026-11-13T18:16:00+09:00"
    assert rows[0].raw["parkingGettime"] == "18:16:00"


async def test_public_raw_set_uses_gw_pages_without_airport_filter_and_retains_metadata():
    session = AsyncFakeSession(
        [
            response(names=("제1주차장", "제2주차장"), total=3, size=2),
            response(page=2, names=("제3주차장",), total=3, size=2),
        ]
    )
    async with KrairportClient(
        kac_service_key="fixture", session=session, retries=0, max_rps=1000
    ) as client:
        result = await client.parking_raw_set(provider="kac", page_size=2, max_pages=2)
    assert result.total_count == 3 and result.page_count == 2 and result.wire_page_metadata
    assert len(result.items) == 3
    for page, call in enumerate(session.calls, 1):
        assert_official_request(call)
        assert "schAirportCode" not in call.params
        assert call.params["pageNo"] == page and call.params["numOfRows"] == 2
    for row in result.items:
        parsed = parse_parking_snapshot_values(row, provider="kac")
        assert parsed.occupied_spaces == 0 and parsed.observed_at.utcoffset() == timedelta(hours=9)


async def test_new_gw_http_403_remains_auth_error_without_retry_or_empty_receipt():
    session = AsyncFakeSession(
        [
            FakeResponse(
                status_code=403,
                text=(
                    "<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>30</returnReasonCode>"
                    "<returnAuthMsg>UNREGISTERED fixture-key</returnAuthMsg>"
                    "</cmmMsgHeader></OpenAPI_ServiceResponse>"
                ),
            )
        ]
    )
    async with KrairportClient(kac_service_key="fixture-key", session=session, retries=3) as client:
        with pytest.raises(KrairportAuthError) as caught:
            await client.parking_raw_set(provider="kac", max_pages=1)
    assert len(session.calls) == 1
    assert "fixture-key" not in str(caught.value)
    assert "403" in str(caught.value)


async def test_new_gw_body_level_auth_failure_is_not_an_empty_success():
    session = AsyncFakeSession(
        [
            FakeResponse(
                text=(
                    "<response><header><resultCode>30</resultCode>"
                    "<resultMsg>UNREGISTERED fixture-key</resultMsg></header></response>"
                )
            )
        ]
    )
    async with KrairportClient(kac_service_key="fixture-key", session=session, retries=0) as client:
        with pytest.raises(KrairportAuthError) as caught:
            await client.parking_raw_set(provider="kac", max_pages=1)
    assert len(session.calls) == 1 and "fixture-key" not in str(caught.value)


async def test_typed_gw_invalid_clock_is_sanitized_instead_of_using_current_time():
    session = AsyncFakeSession([response(clock="99:00:00")])
    client = KacClient("fixture", session=session, retries=0)
    with pytest.raises(KrairportParseError, match="timestamp") as caught:
        await client.parking_status(airport_code="GMP")
    assert "99:00:00" not in str(caught.value)


def test_parking_catalog_points_to_the_new_service_and_registration_page():
    (row,) = api_catalog("parking_status", provider="kac")
    assert row.dataset == "kac_airport_parking_congestion"
    assert row.endpoint == CONTRACT["endpoint"]
    assert row.service == "parking-realtime-status" and row.operation == "info"
    assert row.service_key_url == CONTRACT["source"]


async def test_registered_gw_25_observed_rows_replay_without_losing_zero_or_raw_values():
    # 실제 수신의 공개 검증 7필드 투영이다. 원 HTTP XML 바이트라고 주장하지 않는다.
    observed = json.loads(
        (Path(__file__).parent / "fixtures/kac_parking_realtime_observed.json").read_text(
            encoding="utf-8"
        )
    )
    root = ElementTree.Element("response")
    header = ElementTree.SubElement(root, "header")
    for name, value in (
        ("resultCode", observed["result_code"]),
        ("resultMsg", observed["result_message"]),
    ):
        ElementTree.SubElement(header, name).text = str(value)
    body = ElementTree.SubElement(root, "body")
    for name, key in (
        ("totalCount", "total_count"),
        ("pageNo", "page_no"),
        ("numOfRows", "num_rows"),
    ):
        ElementTree.SubElement(body, name).text = str(observed[key])
    items = ElementTree.SubElement(body, "items")
    for row in observed["items"]:
        item = ElementTree.SubElement(items, "item")
        for name, value in row.items():
            ElementTree.SubElement(item, name).text = value
    session = AsyncFakeSession([FakeResponse(text=ElementTree.tostring(root, encoding="unicode"))])
    async with KrairportClient(kac_service_key="fixture", session=session, retries=0) as client:
        result = await client.parking_raw_set(provider="kac", page_size=100, max_pages=1)
    assert result.items == tuple(observed["items"])
    assert result.total_count == 25 and result.page_count == 1 and result.wire_page_metadata
    parsed = [parse_parking_snapshot_values(row, provider="kac") for row in result.items]
    assert any(value.occupied_spaces == 0 for value in parsed)
    assert all(value.total_spaces > 0 for value in parsed)
    assert all(value.observed_at.utcoffset() == timedelta(hours=9) for value in parsed)
