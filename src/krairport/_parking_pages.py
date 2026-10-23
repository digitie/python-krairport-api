"""주차장 원천 페이지의 유한 완결성 검증. 원천 total 누락은 실패한다."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from krairport.enums import Provider
from krairport.exceptions import KrairportParseError
from krairport.models import ParkingRawSet


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or value is None:
        raise KrairportParseError(f"parking {name} metadata is missing or invalid")
    text = str(value)
    if not text.isascii() or not text.isdigit():
        raise KrairportParseError(f"parking {name} metadata is not a nonnegative integer")
    return int(text)


async def collect_parking_pages(
    fetch_page: Callable[[int, int], Awaitable[Mapping[str, Any]]],
    extract_items: Callable[[Mapping[str, Any]], list[dict[str, Any]]],
    *,
    provider: Provider,
    page_size: int,
    max_pages: int,
) -> ParkingRawSet:
    if type(page_size) is not int or not 1 <= page_size <= 1000:
        raise ValueError("page_size must be 1..1000")
    if type(max_pages) is not int or not 1 <= max_pages <= 20:
        raise ValueError("max_pages must be 1..20")
    rows: list[dict[str, Any]] = []
    total: int | None = None
    seen: set[bytes] = set()
    byte_count = 0
    wire_page_metadata = True
    for page_no in range(1, max_pages + 1):
        data = await fetch_page(page_no, page_size)
        response = data.get("response", data)
        body = response.get("body") if isinstance(response, Mapping) else None
        if not isinstance(body, Mapping):
            raise KrairportParseError("parking response body is missing")
        observed_total = _integer(body.get("totalCount"), "totalCount")
        if total is None:
            total = observed_total
            if total > page_size * max_pages:
                raise KrairportParseError("parking total exceeds bounded page budget")
        elif observed_total != total:
            raise KrairportParseError("parking total changed between pages")
        for name, expected in (("pageNo", page_no), ("numOfRows", page_size)):
            if name in body:
                if _integer(body[name], name) != expected:
                    raise KrairportParseError(f"parking {name} does not match request")
            else:
                wire_page_metadata = False
        items = extract_items(data)
        if len(items) != min(page_size, max(total - len(rows), 0)):
            raise KrairportParseError("parking page size does not match source total")
        for item in items:
            body_bytes = json.dumps(
                item, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode()
            byte_count += len(body_bytes)
            if byte_count > 8 * 1024 * 1024:
                raise KrairportParseError("parking raw set exceeds byte budget")
            digest = hashlib.sha256(body_bytes).digest()
            if digest in seen:
                raise KrairportParseError("parking response repeats an identical row/page")
            seen.add(digest)
        rows.extend(items)
        if len(rows) == total:
            return ParkingRawSet(
                provider=provider,
                items=tuple(rows),
                total_count=total,
                page_count=page_no,
                page_size=page_size,
                wire_page_metadata=wire_page_metadata,
            )
    raise KrairportParseError("parking page budget exhausted before source total")
