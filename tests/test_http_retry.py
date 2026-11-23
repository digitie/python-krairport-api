"""재시도 backoff·jitter와 `Retry-After` 존중."""

from __future__ import annotations

from email.utils import formatdate

import httpx
import pytest

import krairport._http as http_module
from krairport import KrairportClient
from krairport._http import HttpClient
from krairport.exceptions import (
    KrairportAuthError,
    KrairportNetworkError,
    KrairportRateLimitError,
    KrairportServerError,
)
from tests.conftest import FakeResponse, FakeSession

OK = {"response": {"header": {"resultCode": "00"}}}


class TimeoutSession:
    def __init__(self) -> None:
        self.calls = 0

    async def get(self, url, *, params, timeout):  # type: ignore[no-untyped-def]
        self.calls += 1
        raise httpx.TimeoutException("timed out")


async def test_transient_status_retries_after_backoff_not_immediately(  # type: ignore[no-untyped-def]
    retry_sleeps, monkeypatch,
) -> None:
    monkeypatch.setattr(http_module, "_random", lambda: 1.0)
    session = FakeSession(
        [
            FakeResponse(status_code=503, text="busy"),
            FakeResponse(status_code=429, text="slow down"),
            FakeResponse(json_data=OK),
        ]
    )
    client = HttpClient("KEY", session=session, retries=3)

    await client.get_json("https://example.test", {})

    assert len(session.calls) == 3
    # 지수 증가(0.5초 → 1초), jitter 상한 쪽.
    assert retry_sleeps == [0.5, 1.0]


def test_backoff_jitter_stays_between_half_and_full_ceiling(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(http_module, "_random", lambda: 0.0)
    assert http_module._backoff_delay(0) == 0.25
    monkeypatch.setattr(http_module, "_random", lambda: 1.0)
    assert http_module._backoff_delay(10) == http_module.RETRY_BACKOFF_MAX


async def test_retry_after_seconds_is_honored(retry_sleeps) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession(
        [
            FakeResponse(status_code=429, text="slow", headers={"Retry-After": "7"}),
            FakeResponse(json_data=OK),
        ]
    )
    client = HttpClient("KEY", session=session, retries=2)

    await client.get_json("https://example.test", {})

    assert retry_sleeps == [7.0]
    assert len(session.calls) == 2


async def test_retry_after_http_date_is_honored(  # type: ignore[no-untyped-def]
    retry_sleeps, monkeypatch,
) -> None:
    now = 1_800_000_000.0
    monkeypatch.setattr(http_module.time, "time", lambda: now)
    session = FakeSession(
        [
            FakeResponse(
                status_code=503,
                headers={"Retry-After": formatdate(now + 12, usegmt=True)},
            ),
            FakeResponse(json_data=OK),
        ]
    )
    client = HttpClient("KEY", session=session, retries=1)

    await client.get_json("https://example.test", {})

    assert retry_sleeps == [12.0]


async def test_long_retry_after_raises_without_waiting(  # type: ignore[no-untyped-def]
    retry_sleeps,
) -> None:
    session = FakeSession(
        [FakeResponse(status_code=429, text="quota", headers={"Retry-After": "3600"})]
    )
    client = HttpClient("KEY", session=session, retries=3, max_retry_after=30)

    with pytest.raises(KrairportRateLimitError) as caught:
        await client.get_json("https://example.test", {})

    assert caught.value.retry_after == 3600.0
    assert retry_sleeps == []
    assert len(session.calls) == 1


async def test_long_retry_after_on_503_raises_server_error_with_hint(  # type: ignore[no-untyped-def]
    retry_sleeps,
) -> None:
    session = FakeSession([FakeResponse(status_code=503, headers={"Retry-After": "600"})])
    client = HttpClient("KEY", session=session, retries=3)

    with pytest.raises(KrairportServerError) as caught:
        await client.get_json("https://example.test", {})

    assert caught.value.retry_after == 600.0
    assert retry_sleeps == []


async def test_last_rate_limit_carries_retry_after(  # type: ignore[no-untyped-def]
    retry_sleeps,
) -> None:
    session = FakeSession(
        [
            FakeResponse(status_code=429, headers={"Retry-After": "2"}),
            FakeResponse(status_code=429, headers={"Retry-After": "2"}),
        ]
    )
    client = HttpClient("KEY", session=session, retries=1)

    with pytest.raises(KrairportRateLimitError) as caught:
        await client.get_json("https://example.test", {})

    assert caught.value.retry_after == 2.0
    assert retry_sleeps == [2.0]


@pytest.mark.parametrize("value", ["", "soon", "-5", "Mon, 99 Foo 2026 00:00:00 GMT"])
async def test_unparseable_retry_after_falls_back_to_backoff(  # type: ignore[no-untyped-def]
    retry_sleeps, value,
) -> None:
    session = FakeSession(
        [
            FakeResponse(status_code=429, headers={"Retry-After": value}),
            FakeResponse(json_data=OK),
        ]
    )
    client = HttpClient("KEY", session=session, retries=1)

    await client.get_json("https://example.test", {})

    assert len(retry_sleeps) == 1
    assert 0.25 <= retry_sleeps[0] <= 0.5


async def test_past_http_date_retry_after_waits_only_backoff(  # type: ignore[no-untyped-def]
    retry_sleeps, monkeypatch,
) -> None:
    now = 1_800_000_000.0
    monkeypatch.setattr(http_module.time, "time", lambda: now)
    monkeypatch.setattr(http_module, "_random", lambda: 1.0)
    session = FakeSession(
        [
            FakeResponse(
                status_code=429,
                headers={"Retry-After": formatdate(now - 60, usegmt=True)},
            ),
            FakeResponse(json_data=OK),
        ]
    )
    client = HttpClient("KEY", session=session, retries=1)

    await client.get_json("https://example.test", {})

    assert retry_sleeps == [0.5]


async def test_rate_limit_without_header_has_no_retry_after() -> None:
    session = FakeSession([FakeResponse(status_code=429, text="too many")])
    client = HttpClient("KEY", session=session, retries=0)

    with pytest.raises(KrairportRateLimitError) as caught:
        await client.get_json("https://example.test", {})

    assert caught.value.retry_after is None


async def test_network_error_retries_with_backoff(  # type: ignore[no-untyped-def]
    retry_sleeps,
) -> None:
    session = TimeoutSession()
    client = HttpClient("KEY", session=session, retries=2)

    with pytest.raises(KrairportNetworkError):
        await client.get_json("https://example.test", {})

    assert session.calls == 3
    assert len(retry_sleeps) == 2


async def test_auth_error_is_not_retried(retry_sleeps) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession([FakeResponse(status_code=403, text="forbidden")])
    client = HttpClient("KEY", session=session, retries=3)

    with pytest.raises(KrairportAuthError):
        await client.get_json("https://example.test", {})

    assert retry_sleeps == []
    assert len(session.calls) == 1


@pytest.mark.parametrize("value", [-1.0, float("inf"), float("nan")])
def test_invalid_max_retry_after_is_rejected(value) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        HttpClient("KEY", session=FakeSession([]), max_retry_after=value)


async def test_client_passes_max_retry_after_to_providers() -> None:
    async with KrairportClient(
        kac_service_key="k", iiac_service_key="k", max_retry_after=5
    ) as client:
        assert client.kac._http._max_retry_after == 5
        assert client.iiac._http._max_retry_after == 5
