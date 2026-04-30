from __future__ import annotations

import pytest

from pykrairport._http import HttpClient
from pykrairport.exceptions import (
    KrairportAuthError,
    KrairportNetworkError,
    KrairportParseError,
    KrairportRateLimitError,
    KrairportRequestError,
    KrairportServerError,
)
from tests.conftest import FakeResponse, FakeSession


class TimeoutSession:
    def get(self, url, *, params, timeout):  # type: ignore[no-untyped-def]
        import requests

        raise requests.Timeout("timed out")


def test_missing_service_key_raises_auth_error() -> None:
    client = HttpClient(None, session=FakeSession([]))

    with pytest.raises(KrairportAuthError):
        client.get_json("https://example.test", {})


def test_http_status_mapping() -> None:
    session = FakeSession([FakeResponse(status_code=429, text="too many")])
    client = HttpClient("KEY", session=session, retries=0)

    with pytest.raises(KrairportRateLimitError):
        client.get_json("https://example.test", {})


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, KrairportAuthError),
        (404, KrairportRequestError),
        (500, KrairportServerError),
    ],
)
def test_more_http_status_mapping(status, expected) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession([FakeResponse(status_code=status, text="error")])
    client = HttpClient("KEY", session=session, retries=0)

    with pytest.raises(expected):
        client.get_json("https://example.test", {})


def test_network_timeout_maps_to_network_error() -> None:
    client = HttpClient("KEY", session=TimeoutSession(), retries=0)

    with pytest.raises(KrairportNetworkError):
        client.get_json("https://example.test", {})


def test_provider_result_code_auth_mapping() -> None:
    payload = {"response": {"header": {"resultCode": "30", "resultMsg": "SERVICE KEY ERROR"}}}
    client = HttpClient("KEY", session=FakeSession([FakeResponse(json_data=payload)]), retries=0)

    with pytest.raises(KrairportAuthError):
        client.get_json("https://example.test", {})


def test_provider_result_code_request_mapping() -> None:
    payload = {"response": {"header": {"resultCode": "03", "resultMsg": "NO DATA"}}}
    client = HttpClient("KEY", session=FakeSession([FakeResponse(json_data=payload)]), retries=0)

    with pytest.raises(KrairportRequestError):
        client.get_json("https://example.test", {})


def test_provider_result_code_server_mapping() -> None:
    payload = {"response": {"header": {"resultCode": "99", "resultMsg": "SERVER ERROR"}}}
    client = HttpClient("KEY", session=FakeSession([FakeResponse(json_data=payload)]), retries=0)

    with pytest.raises(KrairportServerError):
        client.get_json("https://example.test", {})


def test_json_parse_failure_raises_parse_error() -> None:
    client = HttpClient("KEY", session=FakeSession([FakeResponse(text="not json")]), retries=0)

    with pytest.raises(KrairportParseError):
        client.get_json("https://example.test", {})


def test_xml_response_success(load_fixture) -> None:  # type: ignore[no-untyped-def]
    client = HttpClient(
        "KEY",
        session=FakeSession([FakeResponse(text=load_fixture("kac_arrivals_single.xml"))]),
        retries=0,
    )

    data = client.get_xml("https://example.test", {})

    assert data["response"]["header"]["resultCode"] == "00"
