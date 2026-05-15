"""공급자 오류 매핑을 포함한 HTTP 도우미."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast

import requests

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


TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class HttpClient:
    def __init__(
        self,
        service_key: str | None,
        *,
        session: SessionLike | None = None,
        timeout: float = 10.0,
        retries: int = 3,
    ) -> None:
        self._service_key = _clean_service_key(service_key)
        self._session = cast(SessionLike, session or requests.Session())
        self._timeout = timeout
        self._retries = retries

    def get_json(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        response = self._request(url, params)
        try:
            data = response.json()
        except ValueError as exc:
            raise KrairportParseError(f"failed to parse JSON response: {exc}") from exc
        if not isinstance(data, dict):
            raise KrairportParseError("JSON response root is not an object")
        _raise_for_data_result(data)
        return data

    def get_xml(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        response = self._request(url, params)
        data = parse_xml(response.text)
        _raise_for_data_result(data)
        return data

    def _request(self, url: str, params: Mapping[str, Any]) -> ResponseLike:
        if not self._service_key:
            raise KrairportAuthError("service key is required for this provider")

        request_params = {
            key: value for key, value in params.items() if value is not None
        } | {"serviceKey": self._service_key}

        last_error: requests.RequestException | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._session.get(
                    url,
                    params=request_params,
                    timeout=self._timeout,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt < self._retries:
                    continue
                raise KrairportNetworkError(str(exc)) from exc

            _raise_for_status(response)
            if response.status_code in TRANSIENT_STATUSES and attempt < self._retries:
                continue
            return response

        raise KrairportNetworkError(str(last_error) if last_error else "request failed")


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
