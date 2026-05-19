"""HTTP transport helpers shared by provider clients."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any, Protocol, cast

import httpx

from krairport._xml import parse_xml, response_header
from krairport.exceptions import (
    KrairportAuthError,
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
    def get(self, url: str, *, params: Mapping[str, Any], timeout: float) -> ResponseLike: ...


class AsyncSessionLike(Protocol):
    async def get(self, url: str, *, params: Mapping[str, Any], timeout: float) -> ResponseLike: ...


TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class HttpClient:
    """Synchronous httpx-backed client used by the public sync facade."""

    def __init__(
        self,
        service_key: str | None,
        *,
        session: SessionLike | None = None,
        timeout: float = 10.0,
        retries: int = 3,
    ) -> None:
        self._service_key = _clean_service_key(service_key)
        self._session = cast(
            SessionLike,
            session or httpx.Client(follow_redirects=True),
        )
        self._timeout = timeout
        self._retries = retries

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if callable(close):
            close()

    def get_json(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        response = self._request(url, params)
        return _response_json(response)

    def get_xml(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        response = self._request(url, params)
        return _response_xml(response)

    def _request(self, url: str, params: Mapping[str, Any]) -> ResponseLike:
        request_params = _request_params(self._service_key, params)
        last_error: httpx.TransportError | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._session.get(
                    url,
                    params=request_params,
                    timeout=self._timeout,
                )
            except httpx.TransportError as exc:
                last_error = exc
                if attempt < self._retries:
                    continue
                raise KrairportNetworkError(str(exc)) from exc

            if response.status_code in TRANSIENT_STATUSES and attempt < self._retries:
                continue
            _raise_for_status(response)
            return response

        raise KrairportNetworkError(str(last_error) if last_error else "request failed")


class AsyncHttpClient:
    """Asynchronous httpx-backed client used by async provider facades."""

    def __init__(
        self,
        service_key: str | None,
        *,
        session: AsyncSessionLike | None = None,
        timeout: float = 10.0,
        retries: int = 3,
    ) -> None:
        self._service_key = _clean_service_key(service_key)
        self._session = cast(
            AsyncSessionLike,
            session or httpx.AsyncClient(follow_redirects=True),
        )
        self._timeout = timeout
        self._retries = retries

    async def __aenter__(self) -> AsyncHttpClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        close = getattr(self._session, "aclose", None)
        if callable(close):
            result = close()
            if _is_awaitable(result):
                await result

    async def get_json(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        response = await self._request(url, params)
        return _response_json(response)

    async def get_xml(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        response = await self._request(url, params)
        return _response_xml(response)

    async def _request(self, url: str, params: Mapping[str, Any]) -> ResponseLike:
        request_params = _request_params(self._service_key, params)
        last_error: httpx.TransportError | None = None
        for attempt in range(self._retries + 1):
            try:
                response = await self._session.get(
                    url,
                    params=request_params,
                    timeout=self._timeout,
                )
            except httpx.TransportError as exc:
                last_error = exc
                if attempt < self._retries:
                    continue
                raise KrairportNetworkError(str(exc)) from exc

            if response.status_code in TRANSIENT_STATUSES and attempt < self._retries:
                continue
            _raise_for_status(response)
            return response

        raise KrairportNetworkError(str(last_error) if last_error else "request failed")


def _is_awaitable(value: object) -> bool:
    return inspect.isawaitable(value)


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


def _raise_for_status(response: ResponseLike) -> None:
    status = response.status_code
    text = response.text[:300]
    if status in {401, 403}:
        raise KrairportAuthError(f"HTTP {status}: {text}")
    if status == 429:
        raise KrairportRateLimitError(f"HTTP {status}: {text}")
    if 400 <= status < 500:
        raise KrairportRequestError(f"HTTP {status}: {text}")
    if 500 <= status < 600:
        raise KrairportServerError(f"HTTP {status}: {text}")


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
