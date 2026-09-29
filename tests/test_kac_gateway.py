"""GW 출도착의 정상·잘린·중복 페이지를 외부 요청 없이 검증한다."""

from copy import deepcopy
from typing import Any

import pytest

from krairport import KrairportClient
from krairport.exceptions import KrairportAuthError, KrairportParseError, KrairportRateLimitError
from tests.conftest import FakeResponse, FakeSession


def _page(
    page: Any = "1", size: Any = "1", total: Any = "1", flight: str = "KE001"
) -> dict[str, Any]:
    return {
        "response": {
            "header": {"resultCode": "00"},
            "body": {
                "pageNo": page,
                "numOfRows": size,
                "totalCount": total,
                "items": {
                    "item": {
                        "flightid": flight,
                        "fid": "000123" + flight,
                        "scheduledatetime": "202609290930",
                        "estimateddatetime": "202609290945",
                        "depAirportCode": "GMP",
                        "arrvAirportCode": "CJU",
                        "depAirport": "김포",
                        "arrAirport": "제주",
                        "line": "국내",
                        "masterflightid": "KE001",
                    }
                },
            },
        }
    }


class GatewaySession(FakeSession):
    """공통 HTTP XML 파서를 통과시키는 중첩 XML fixture."""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        from xml.etree import ElementTree as ET

        def append(parent: ET.Element, data: dict[str, Any]) -> None:
            for key, value in data.items():
                element = ET.SubElement(parent, key)
                if isinstance(value, dict):
                    append(element, value)
                elif value is not None:
                    element.text = str(value)

        responses = []
        for page in pages:
            root = ET.Element("response")
            append(root, page["response"])
            responses.append(FakeResponse(text=ET.tostring(root, encoding="unicode")))
        super().__init__(responses)


async def test_gateway_reads_clamped_pages_and_both_directions() -> None:
    arrival = _page(flight="KE002")
    row = arrival["response"]["body"]["items"]["item"]
    row["arrAirportCode"] = row.pop("arrvAirportCode")
    session = GatewaySession(
        [_page(total="2"), _page(page="2", total="2", flight="KE003"), arrival]
    )
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        flights = await client.kac.flight_status(
            airport_code="GMP", searchday="20260929", max_pages=3
        )
    assert [f.flight_id for f in flights] == ["KE001", "KE003", "KE002"]
    assert [str(f.direction) for f in flights] == ["departure", "departure", "arrival"]
    assert flights[0].flight_unique_id == "000123KE001"
    assert flights[0].scheduled_at.isoformat() == "2026-09-29T09:30:00+09:00"
    assert flights[0].departure_airport_name == "김포"
    assert flights[0].arrival_airport_name == "제주"
    assert flights[0].arrival_airport_code == flights[2].arrival_airport_code == "CJU"
    assert flights[0].line_type == "국내"
    assert flights[0].raw["masterflightid"] == "KE001"
    assert [c.params["pageNo"] for c in session.calls] == [1, 2, 1]
    assert all(c.params["numOfRows"] == 100 for c in session.calls)
    assert [c.url.rsplit("/", 1)[1] for c in session.calls] == ["depart", "depart", "arrival"]


@pytest.mark.parametrize("method", ["departures", "arrivals", "flight_status"])
@pytest.mark.parametrize(
    "code,error", [("22", KrairportRateLimitError), ("30", KrairportAuthError)]
)
async def test_gateway_error_envelope_is_never_an_empty_success(method, code, error):
    session = FakeSession([FakeResponse(text=(
        "<OpenAPI_ServiceResponse><cmmMsgHeader>"
        f"<returnReasonCode>{code}</returnReasonCode>"
        "<returnAuthMsg>fixture-error</returnAuthMsg>"
        "</cmmMsgHeader></OpenAPI_ServiceResponse>"
    ))])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        with pytest.raises(error):
            await getattr(client.kac, method)(airport_code="GMP", searchday="20260929")
    assert len(session.calls) == 1


async def test_gateway_rejects_repeated_fid_even_when_schedule_changes():
    first = _page(total="2")
    second = _page(page="2", total="2")
    second["response"]["body"]["items"]["item"]["scheduledatetime"] = "202609291000"
    session = GatewaySession([first, second, _page(flight="KE002")])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError):
            await client.kac.flight_status(airport_code="GMP", searchday="20260929")
    assert len(session.calls) == 2


@pytest.mark.parametrize("method", ["departures", "arrivals", "flight_status"])
@pytest.mark.parametrize("value", ["20260929", "private-fixture-value"])
async def test_gateway_rejects_missing_time_without_leaking_raw_values(method, value):
    import traceback
    page = _page()
    page["response"]["body"]["items"]["item"]["scheduledatetime"] = value
    session = GatewaySession([page, _page(flight="KE002")])
    query_day = "20260929"
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError) as caught:
            await getattr(client.kac, method)(airport_code="GMP", searchday=query_day)
    assert value not in str(caught.value)
    assert value not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("method", ["departures", "arrivals"])
async def test_gateway_list_rejects_missing_success_header(method):
    page = _page()
    page["response"].pop("header")
    session = GatewaySession([page])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError):
            await getattr(client.kac, method)(airport_code="GMP")


@pytest.mark.parametrize("field", ["pageNo", "numOfRows", "totalCount"])
@pytest.mark.parametrize("value", [None, "-1", "1.5", "garbage", True])
async def test_gateway_rejects_invalid_page_metadata(field: str, value: Any) -> None:
    page = _page()
    page["response"]["body"][field] = value
    session = GatewaySession([page])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError):
            await client.kac.flight_status(airport_code="GMP", searchday="20260929")
    assert len(session.calls) == 1


@pytest.mark.parametrize(
    "fault",
    [
        "empty",
        "repeated",
        "changed_total",
        "changed_size",
        "wrong_page",
        "missing_header",
        "missing_body",
        "no_id",
        "no_time",
    ],
)
async def test_gateway_never_returns_partial_success(fault: str) -> None:
    first = _page(total="2")
    second = _page(page="2", total="2", flight="KE002")
    if fault == "empty":
        second["response"]["body"]["items"] = None
    elif fault == "repeated":
        second["response"]["body"]["items"] = deepcopy(first["response"]["body"]["items"])
    elif fault == "changed_total":
        second["response"]["body"]["totalCount"] = "3"
    elif fault == "changed_size":
        second["response"]["body"]["numOfRows"] = "2"
    elif fault == "wrong_page":
        second["response"]["body"]["pageNo"] = "1"
    elif fault == "missing_header":
        second["response"].pop("header")
    elif fault == "missing_body":
        second["response"].pop("body")
    elif fault == "no_id":
        second["response"]["body"]["items"]["item"].pop("flightid")
    elif fault == "no_time":
        second["response"]["body"]["items"]["item"].pop("scheduledatetime")
    session = GatewaySession([first, second])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError):
            await client.kac.flight_status(airport_code="GMP", searchday="20260929")
    assert len(session.calls) == 2


async def test_gateway_budget_is_shared_between_directions() -> None:
    session = GatewaySession([_page(total="2"), _page(page="2", total="2", flight="KE002")])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        with pytest.raises(KrairportParseError, match="예산"):
            await client.kac.flight_status(airport_code="GMP", searchday="20260929", max_pages=2)
    assert len(session.calls) == 2


async def test_gateway_empty_success_needs_both_directions() -> None:
    empty = _page(total="0")
    empty["response"]["body"]["items"] = None
    session = GatewaySession([empty, empty])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        assert await client.kac.flight_status(airport_code="GMP", searchday="20260929") == []
    assert len(session.calls) == 2


async def test_gateway_403_never_retries_or_becomes_empty() -> None:
    session = FakeSession([FakeResponse(status_code=403)])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=3) as client:
        with pytest.raises(KrairportAuthError):
            await client.kac.flight_status(airport_code="GMP", searchday="20260929")
    assert len(session.calls) == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_pages": 0},
        {"max_pages": 101},
        {"num_of_rows": 0},
        {"num_of_rows": True},
        {"searchday": "20260230"},
        {"searchday": "2026-09-29"},
    ],
)
async def test_gateway_invalid_request_never_calls_provider(kwargs: dict[str, Any]) -> None:
    session = FakeSession([])
    async with KrairportClient(kac_service_key="test-key", session=session, retries=0) as client:
        with pytest.raises(ValueError):
            await client.kac.flight_status(
                **{"airport_code": "GMP", "searchday": "20260929", **kwargs}
            )
    assert session.calls == []
