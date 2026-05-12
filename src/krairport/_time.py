"""KST 기준 datetime 파싱 도우미."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from krairport._convert import strip_or_none

KST: tzinfo
try:
    KST = ZoneInfo("Asia/Seoul")
except ZoneInfoNotFoundError:
    KST = timezone(timedelta(hours=9), "Asia/Seoul")


def parse_kst_datetime(value: Any, *, base_date: str | date | None = None) -> datetime | None:
    """공급자 timestamp 값을 timezone 정보가 있는 KST datetime으로 파싱합니다."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=KST) if value.tzinfo is None else value.astimezone(KST)
    if isinstance(value, date):
        return datetime.combine(value, time.min, KST)

    text = strip_or_none(value)
    if text is None:
        return None

    digits = _timestamp_digits(text)
    if len(digits) in {14, 12, 8}:
        return _parse_digits(digits)
    if len(digits) in {4, 6} and base_date is not None:
        base = _parse_base_date(base_date)
        return _combine_date_and_time(base, digits)
    raise ValueError(f"unsupported KST timestamp: {value!r}")


def combine_date_time(date_value: str | date, time_value: Any) -> datetime | None:
    text = strip_or_none(time_value)
    if text is None:
        return None
    digits = _timestamp_digits(text)
    if len(digits) not in {4, 6}:
        return parse_kst_datetime(text)
    return _combine_date_and_time(_parse_base_date(date_value), digits)


def _timestamp_digits(text: str) -> str:
    normalized = text.strip()
    if "e" in normalized.lower():
        try:
            normalized = format(Decimal(normalized), "f")
        except InvalidOperation as exc:
            raise ValueError(f"invalid scientific timestamp: {text!r}") from exc
    return "".join(ch for ch in normalized if ch.isdigit())


def _parse_digits(digits: str) -> datetime:
    if len(digits) == 8:
        return datetime.strptime(digits, "%Y%m%d").replace(tzinfo=KST)
    if len(digits) == 12:
        return datetime.strptime(digits, "%Y%m%d%H%M").replace(tzinfo=KST)
    if len(digits) == 14:
        return datetime.strptime(digits, "%Y%m%d%H%M%S").replace(tzinfo=KST)
    raise ValueError(f"unsupported timestamp digits: {digits!r}")


def _parse_base_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    digits = _timestamp_digits(value)
    if len(digits) != 8:
        raise ValueError(f"base_date must be YYYYMMDD: {value!r}")
    return datetime.strptime(digits, "%Y%m%d").date()


def _combine_date_and_time(base: date, digits: str) -> datetime:
    if digits.startswith("24"):
        if digits not in {"2400", "240000"}:
            raise ValueError(f"invalid 24-hour boundary time: {digits!r}")
        return datetime.combine(base + timedelta(days=1), time.min, KST)
    fmt = "%H%M%S" if len(digits) == 6 else "%H%M"
    parsed_time = datetime.strptime(digits, fmt).time()
    return datetime.combine(base, parsed_time, KST)
