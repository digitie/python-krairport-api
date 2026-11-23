"""공급자가 공유하는 비동기 HTTP 전송 도우미."""

from __future__ import annotations

import asyncio
import inspect
import math
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Protocol, cast
from urllib.parse import quote

import httpx

from krairport._httpx import send_after_token
from krairport._ratelimit import AsyncTokenBucket
from krairport._xml import parse_xml, response_header
from krairport.exceptions import (
    KrairportAuthError,
    KrairportError,
    KrairportNetworkError,
    KrairportParseError,
    KrairportRateLimitError,
    KrairportRequestError,
    KrairportServerError,
)


class ResponseLike(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...




class SessionLike(Protocol):
    async def get(self, url: str, *, params: Mapping[str, Any], timeout: float) -> ResponseLike: ...


TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
#: 재시도 간격의 기준(초). n번째 재시도 전
#: `min(RETRY_BACKOFF_MAX, BASE * 2**n)`의 50~100%를 기다린다.
RETRY_BACKOFF_BASE = 0.5
RETRY_BACKOFF_MAX = 8.0
#: 공급자가 `Retry-After`로 이보다 긴 대기를 요구하면 기다리지 않고
#: 예외(`retry_after` 포함)로 돌려준다.
DEFAULT_MAX_RETRY_AFTER = 30.0

# 테스트가 실제로 기다리지 않도록 교체할 수 있는 대기·난수 함수.
_sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
_random: Callable[[], float] = random.random




class HttpClient:
    """공급자가 사용하는 비동기 HTTP 클라이언트."""

    def __init__(
        self,
        service_key: str | None,
        *,
        session: SessionLike | None = None,
        timeout: float = 10.0,
        retries: int = 3,
        max_rps: float = 5.0,
        rate_limiter: AsyncTokenBucket | None = None,
        max_retry_after: float = DEFAULT_MAX_RETRY_AFTER,
    ) -> None:
        if not math.isfinite(max_retry_after) or max_retry_after < 0:
            raise ValueError("max_retry_after must be a finite number >= 0")
        self.rate_limiter = rate_limiter if rate_limiter is not None else AsyncTokenBucket(max_rps)
        if session is not None and not inspect.iscoroutinefunction(session.get):
            raise TypeError("session.get must be async")
        self._owns_session = session is None
        self._closed = False
        self._service_key = _clean_service_key(service_key)
        self._session = cast(
            SessionLike,
            session if session is not None else httpx.AsyncClient(follow_redirects=True),
        )
        self._timeout = timeout
        self._retries = retries
        self._max_retry_after = max_retry_after

    async def __aenter__(self) -> HttpClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        close = getattr(self._session, "aclose", None)
        if self._owns_session and callable(close):
            await close()
        self._closed = True

    async def get_json(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        try:
            response = await self._request(url, params)
            return _response_json(response)
        except KrairportError as exc:
            exc.args = (_redact_key(str(exc), self._service_key),)
            raise exc from None

    async def get_xml(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        try:
            response = await self._request(url, params)
            return _response_xml(response)
        except KrairportError as exc:
            exc.args = (_redact_key(str(exc), self._service_key),)
            raise exc from None

    async def _request(self, url: str, params: Mapping[str, Any]) -> ResponseLike:
        if self._closed:
            raise RuntimeError("KrairportClient is closed")
        request_params = _request_params(self._service_key, params)
        last_error: httpx.HTTPError | None = None
        for attempt in range(self._retries + 1):
            await self.rate_limiter.acquire()
            try:
                if isinstance(self._session, httpx.AsyncClient):
                    request = self._session.build_request(
                        "GET", url, params=request_params, timeout=self._timeout
                    )
                    response = await send_after_token(self._session, request, self.rate_limiter)
                else:
                    response = await self._session.get(
                        url, params=request_params, timeout=self._timeout
                    )
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._retries:
                    await _sleep(_backoff_delay(attempt))
                    continue
                raise KrairportNetworkError(_redact_key(str(exc), self._service_key)) from None

            if response.status_code in TRANSIENT_STATUSES:
                retry_after = _retry_after_seconds(response)
                # 즉시 재호출하지 않는다. 공급자가 상한보다 긴 대기를 요구하면 붙잡지 않고 돌려준다.
                if attempt < self._retries and (
                    retry_after is None or retry_after <= self._max_retry_after
                ):
                    delay = _backoff_delay(attempt)
                    await _sleep(delay if retry_after is None else max(retry_after, delay))
                    continue
                _raise_for_status(response, retry_after=retry_after)
            _raise_for_status(response)
            return response

        raise KrairportNetworkError(str(last_error) if last_error else "request failed")




def _redact_key(text: str, key: str | None) -> str:
    if not key:
        return text
    return text.replace(key, "<REDACTED>").replace(quote(key, safe=""), "<REDACTED>")


def _request_params(service_key: str | None, params: Mapping[str, Any]) -> dict[str, Any]:
    if not service_key:
        raise KrairportAuthError("service key is required for this provider")
    return {key: value for key, value in params.items() if value is not None} | {
        "serviceKey": service_key
    }


def _response_json(response: ResponseLike) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise KrairportParseError(f"failed to parse JSON response: {exc}") from exc
    if not isinstance(data, dict):
        raise KrairportParseError("JSON response root is not an object")
    _raise_for_data_result(data)
    return data


def _response_xml(response: ResponseLike) -> dict[str, Any]:
    data = parse_xml(response.text)
    _raise_for_data_result(data)
    return data


def _clean_service_key(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _backoff_delay(attempt: int) -> float:
    """지수 backoff + jitter(상한의 50~100%).

    함께 실패한 호출자가 같은 순간에 다시 몰리지 않게 한다.
    """
    ceiling = min(RETRY_BACKOFF_MAX, RETRY_BACKOFF_BASE * (2.0**attempt))
    return ceiling * (0.5 + 0.5 * _random())


def _retry_after_seconds(response: ResponseLike) -> float | None:
    """`Retry-After`(정수 초 또는 HTTP-date)를 초로 읽는다. 없거나 해석할 수 없으면 `None`."""
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    try:
        raw = headers.get("Retry-After")
    except Exception:  # noqa: BLE001 - header 접근 실패는 값 없음으로 본다.
        return None
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    if value.isascii() and value.isdigit():
        return float(int(value))
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    seconds = (when - datetime.fromtimestamp(time.time(), tz=UTC)).total_seconds()
    return max(0.0, seconds) if math.isfinite(seconds) else None


def _raise_for_status(response: ResponseLike, *, retry_after: float | None = None) -> None:
    status = response.status_code
    text = response.text[:300]
    if status in {401, 403}:
        raise KrairportAuthError(f"HTTP {status}: {text}")
    if status == 429:
        raise KrairportRateLimitError(f"HTTP {status}: {text}", retry_after=retry_after)
    if 400 <= status < 500:
        raise KrairportRequestError(f"HTTP {status}: {text}")
    if 500 <= status < 600:
        raise KrairportServerError(f"HTTP {status}: {text}", retry_after=retry_after)


def _raise_for_data_result(data: Mapping[str, Any]) -> None:
    header = _find_header(data)
    code = str(header.get("resultCode", "")).strip()
    message = str(header.get("resultMsg", "")).strip()
    if not code or code in {"00", "0", "NORMAL_CODE"}:
        return
    upper = f"{code} {message}".upper()
    if code in {"20", "30", "31"} or "SERVICE_KEY" in upper or "AUTH" in upper:
        raise KrairportAuthError(message or f"provider result code {code}")
    if code in {"22"} or "LIMIT" in upper or "QUOTA" in upper:
        raise KrairportRateLimitError(message or f"provider result code {code}")
    if code.startswith("5") or code in {"04", "99"}:
        raise KrairportServerError(message or f"provider result code {code}")
    raise KrairportRequestError(message or f"provider result code {code}")


def _find_header(data: Mapping[str, Any]) -> Mapping[str, Any]:
    if "OpenAPI_ServiceResponse" in data:
        envelope = data["OpenAPI_ServiceResponse"]
        header = envelope.get("cmmMsgHeader") if isinstance(envelope, Mapping) else None
        if not isinstance(header, Mapping) or not header.get("returnReasonCode"):
            raise KrairportParseError("공공데이터 GW 오류 헤더가 올바르지 않습니다.")
        code = str(header["returnReasonCode"]).strip()
        if code in {"01", "05"}:
            raise KrairportServerError("공공데이터 GW 서버 장애 또는 응답 시간 초과")
        if code == "23":
            raise KrairportRateLimitError("공공데이터 GW 접근 호출량 제한")
        return {
            "resultCode": header["returnReasonCode"],
            "resultMsg": header.get("returnAuthMsg", ""),
        }
    if "response" in data and isinstance(data["response"], Mapping):
        response = data["response"]
        header = response.get("header")
        if isinstance(header, Mapping):
            return header
    header = data.get("header")
    if isinstance(header, Mapping):
        return header
    xml_header = response_header(data)
    return xml_header
