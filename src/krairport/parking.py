"""수집 승인용 주차장 원문 값 검증. 기존 느슨한 status API와 분리한다."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from krairport._time import parse_kst_datetime
from krairport.enums import Provider, normalize_provider
from krairport.exceptions import KrairportParseError
from krairport.models import ParkingSnapshotValues
from krairport.types import ProviderLike


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise KrairportParseError("parking count must be a nonnegative integer")
    if isinstance(value, int) and not 0 <= value <= 999999999:
        raise KrairportParseError("parking count must be a bounded nonnegative integer")
    text = str(value).strip()
    if not 1 <= len(text) <= 9 or not text.isascii() or not text.isdigit():
        raise KrairportParseError("parking count must be a bounded nonnegative integer")
    return int(text)


def parse_parking_snapshot_values(
    raw: Mapping[str, Any],
    *,
    provider: ProviderLike,
) -> ParkingSnapshotValues:
    """기관 원문의 현황 숫자와 실제 KST 시각을 반환한다. 원문은 오류에 포함하지 않는다."""
    if not isinstance(raw, Mapping):
        raise KrairportParseError("parking observation must be an object")
    selected = normalize_provider(provider)
    if selected is Provider.KAC:
        capacity = _count(raw.get("parkingFullSpace"))
        occupied = _count(raw.get("parkingIstay"))
        day, clock = raw.get("parkingGetdate"), raw.get("parkingGettime")
        if (
            not isinstance(day, str)
            or not isinstance(clock, str)
            or re.fullmatch(r"(?:[0-9]{8}|[0-9]{4}-[0-9]{2}-[0-9]{2})", day.strip()) is None
            or re.fullmatch(r"(?:[0-9]{6}|[0-9]{2}:[0-9]{2}:[0-9]{2})", clock.strip()) is None
        ):
            raise KrairportParseError("parking KAC observation timestamp is malformed")
        text = day.strip().replace("-", "") + clock.strip().replace(":", "")
    else:
        capacity = _count(raw.get("parkingarea"))
        occupied = _count(raw.get("parking"))
        value = raw.get("datetm")
        if (
            not isinstance(value, str)
            or re.fullmatch(
                r"(?:[0-9]{12}|[0-9]{14}|[0-9]{4}-[0-9]{2}-[0-9]{2} "
                r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?)",
                value.strip(),
            )
            is None
        ):
            raise KrairportParseError("parking IIAC observation timestamp is malformed")
        text = value.strip()
    try:
        observed_at = parse_kst_datetime(text, require_time=True)
    except (TypeError, ValueError, OverflowError):
        raise KrairportParseError("parking observation timestamp is invalid") from None
    if observed_at is None:
        raise KrairportParseError("parking observation timestamp is missing")
    return ParkingSnapshotValues(
        total_spaces=capacity, occupied_spaces=occupied, observed_at=observed_at
    )
