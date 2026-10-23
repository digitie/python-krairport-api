"""주차장 전체 페이지의 메타·중복·변동·상한을 네트워크 없이 검증한다."""

import pytest

from krairport import KrairportClient, KrairportParseError, ParkingRawSet
from krairport._parking_pages import collect_parking_pages
from krairport.enums import Provider
from tests.conftest import AsyncFakeSession, FakeResponse


def body(total=3, page=1, size=2, items=None):
    return {
        "response": {
            "header": {"resultCode": "00"},
            "body": {
                "totalCount": total,
                "pageNo": page,
                "numOfRows": size,
                "items": {"item": items if items is not None else [{"id": "a"}, {"id": "b"}]},
            },
        }
    }


async def run(pages, **kwargs):
    async def fetch(page, size):
        return pages[page - 1]

    return await collect_parking_pages(
        fetch,
        lambda data: data["response"]["body"]["items"]["item"],
        provider=Provider.KAC,
        page_size=2,
        max_pages=3,
        **kwargs,
    )


async def test_full_receipt_and_missing_echo_are_distinct():
    result = await run([body(), body(page=2, items=[{"id": "c"}])])
    assert isinstance(result, ParkingRawSet)
    assert result.total_count == 3 and result.page_count == 2 and result.wire_page_metadata
    assert result.items[-1]["id"] == "c"
    data = body(total=2)
    del data["response"]["body"]["pageNo"]
    result = await run([data])
    assert not result.wire_page_metadata and result.total_count == 2


@pytest.mark.parametrize(
    "pages",
    [
        [body(total=None)],
        [body(total=-1)],
        [body(total=True)],
        [body(total=7)],
        [body(page=2)],
        [body(size=3)],
        [body(items=[{"id": "a"}])],
        [body(), body(total=4, page=2)],
        [body(total=4), body(total=4, page=2)],
        [body(total=0)],
    ],
)
async def test_missing_changing_truncated_or_repeated_page_is_rejected(pages):
    with pytest.raises(KrairportParseError):
        await run(pages)


async def test_authoritative_empty_receipt():
    result = await run([body(total=0, items=[])])
    assert result.total_count == 0 and result.items == () and result.page_count == 1


@pytest.mark.parametrize("provider", ["kac", "iiac"])
async def test_public_client_uses_real_provider_paths_and_pagination(provider):
    if provider == "kac":

        def response(page, names):
            items = "".join(f"<item><id>{name}</id></item>" for name in names)
            return FakeResponse(
                text=f"<response><header><resultCode>00</resultCode></header><body><totalCount>3</totalCount><pageNo>{page}</pageNo><numOfRows>2</numOfRows><items>{items}</items></body></response>"
            )
    else:

        def response(page, names):
            data = body(page=page, items=[{"id": name} for name in names])
            data["response"]["header"] = {"resultCode": "00"}
            return FakeResponse(json_data=data)

    session = AsyncFakeSession([response(1, ["a", "b"]), response(2, ["c"])])
    async with KrairportClient(
        kac_service_key="fixture", iiac_service_key="fixture", session=session, max_rps=1000
    ) as client:
        result = await client.parking_raw_set(provider=provider, page_size=2)
    assert len(result.items) == 3
    assert [call.params["pageNo"] for call in session.calls] == [1, 2]
    assert all(call.params["numOfRows"] == 2 for call in session.calls)
    expected = (
        "AirportParking/airportparkingRT"
        if provider == "kac"
        else "StatusOfParking/getTrackingParking"
    )
    assert all(call.url.endswith(expected) for call in session.calls)


@pytest.mark.parametrize(
    "items",
    [
        "provider schema error",
        {"unexpected": []},
        {"item": [], "unexpected": "failure"},
        ["invalid"],
        {"item": "provider schema error"},
    ],
)
async def test_malformed_empty_never_becomes_authoritative_receipt(items):
    data = body(total=0, items=[])
    data["response"]["body"]["items"] = items

    async def fetch(page, size):
        return data

    with pytest.raises(KrairportParseError):
        await collect_parking_pages(
            fetch, lambda data: [], provider=Provider.KAC, page_size=2, max_pages=3
        )


@pytest.mark.parametrize("items", ["", None, {}, [], {"item": []}])
async def test_normal_empty_container_remains_valid(items):
    data = body(total=0, items=[])
    data["response"]["body"]["items"] = items

    async def fetch(page, size):
        return data

    result = await collect_parking_pages(
        fetch, lambda data: [], provider=Provider.KAC, page_size=2, max_pages=3
    )
    assert result.total_count == 0 and result.items == ()


@pytest.mark.parametrize("key", ["totalCount", "pageNo", "numOfRows"])
async def test_unbounded_integer_metadata_is_parse_error(key):
    data = body(total=2)
    data["response"]["body"][key] = "1" * 4301
    with pytest.raises(KrairportParseError):
        await run([data])


@pytest.mark.parametrize("provider", [Provider.KAC, Provider.IIAC])
@pytest.mark.parametrize(
    "header", [None, {}, {"resultMsg": "upstream error"}, {"resultCode": "99"}]
)
async def test_full_set_requires_explicit_success_header(provider, header):
    data = body(total=0, items=[])
    if header is None:
        data["response"].pop("header", None)
    else:
        data["response"]["header"] = header

    async def fetch(page, size):
        return data

    with pytest.raises(KrairportParseError, match="explicit success"):
        await collect_parking_pages(
            fetch, lambda data: [], provider=provider, page_size=2, max_pages=3
        )


async def test_full_set_missing_items_is_not_empty_receipt():
    data = body(total=0, items=[])
    del data["response"]["body"]["items"]
    with pytest.raises(KrairportParseError):
        await run([data])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "\ud800", object()])
async def test_nonfinite_or_unserializable_item_is_sanitized_parse_error(value):
    with pytest.raises(KrairportParseError, match="safely serialized"):
        await run([body(total=1, items=[{"value": value}])])
