"""두 공급자·재시도·redirect·debug의 공통 예산을 검증합니다."""

import asyncio
import time

import httpx
import pytest

from krairport import AsyncTokenBucket, KrairportClient
from krairport.exceptions import KrairportAuthError
from krairport.providers import IiacClient, KacClient

XML = "<response><header><resultCode>00</resultCode></header><body><items/></body></response>"
JSON = {"response": {"header": {"resultCode": "00"}, "body": {"items": []}}}


class CountingBucket(AsyncTokenBucket):
    def __init__(self):
        super().__init__(100)
        self.calls = 0

    async def acquire(self):
        self.calls += 1
        await super().acquire()


async def test_kac_iiac_retry_redirect_and_debug_share_budget():
    bucket = CountingBucket()
    sent = []

    def respond(request):
        sent.append(request.url.path)
        if len(sent) == 1:
            return httpx.Response(503)
        if len(sent) == 2:
            return httpx.Response(307, headers={"Location": "/xml-result"})
        return httpx.Response(200, text=XML) if len(sent) == 3 else httpx.Response(200, json=JSON)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), follow_redirects=True
    ) as session:
        async with KrairportClient("key", "key", session=session, rate_limiter=bucket) as client:
            assert await client.kac_raw_items("service", "operation") == []
            run = await client.debug_iiac_raw_items(service="service", operation="operation")
            assert run.error is None
            assert run.processed == []
            assert client.kac._http.rate_limiter is client.iiac._http.rate_limiter is bucket
        assert bucket.calls == len(sent) == 4
        assert not session.is_closed
        with pytest.raises(RuntimeError, match="closed"):
            await client.iiac_raw_items("service", "operation")
        assert len(sent) == 4


async def test_injected_providers_and_multiple_clients_share_requested_budget():
    bucket = CountingBucket()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=XML))
    ) as session:
        kac = KacClient("key", session=session)
        iiac = IiacClient("key", session=session)
        async with KrairportClient(kac_client=kac, iiac_client=iiac, rate_limiter=bucket) as first:
            async with KrairportClient(
                "key", "key", session=session, rate_limiter=bucket
            ) as second:
                await first.kac_raw_items("service", "operation")
                await second.kac_raw_items("service", "operation")
        assert bucket.calls == 2


async def test_concurrent_requests_obey_capacity_one_budget():
    sent = []

    def respond(request):
        sent.append(time.monotonic())
        return httpx.Response(200, json=JSON)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as session:
        async with KrairportClient(
            "key", "key", session=session, rate_limiter=AsyncTokenBucket(20, capacity=1)
        ) as client:
            await asyncio.gather(*(client.iiac_raw_items("service", "operation") for _ in range(5)))
    assert sent[-1] - sent[0] >= 0.195


@pytest.mark.parametrize("rate", [0, -1, float("inf"), float("nan"), True])
def test_invalid_rate_rejected(rate):
    with pytest.raises(ValueError):
        KrairportClient("key", "key", max_rps=rate)


def test_sync_session_and_surface_removed():
    assert not hasattr(KrairportClient, "aio")
    assert not hasattr(KrairportClient, "__enter__")
    with httpx.Client() as session:
        with pytest.raises(TypeError, match="must be async"):
            KrairportClient("key", "key", session=session)


async def test_provider_body_auth_error_masks_echoed_key():
    payload = {"response": {"header": {"resultCode": "30", "resultMsg": "secret-key"}}}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as session:
        async with KrairportClient("secret-key", "secret-key", session=session) as client:
            with pytest.raises(KrairportAuthError) as error:
                await client.iiac_raw_items("service", "operation")
            assert "secret-key" not in str(error.value)
            run = await client.debug_iiac_raw_items(service="service", operation="operation")
            assert "secret-key" not in repr(run.error)
