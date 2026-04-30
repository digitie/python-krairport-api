"""Conversion helpers for provider response values."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, TypeVar

T = TypeVar("T")


def strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "-"}:
        return None
    return text


def first_value(record: Mapping[str, Any], *keys: str) -> Any:
    """Return the first non-empty value for the given provider field names."""

    for key in keys:
        value = strip_or_none(record.get(key))
        if value is not None:
            return value
    return None


def to_int_or_none(value: Any) -> int | None:
    text = strip_or_none(value)
    if text is None:
        return None
    text = text.replace(",", "")
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid integer value: {value!r}") from exc


def to_float_or_none(value: Any) -> float | None:
    text = strip_or_none(value)
    if text is None:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"invalid float value: {value!r}") from exc


def to_bool_or_none(value: Any) -> bool | None:
    text = strip_or_none(value)
    if text is None:
        return None
    normalized = text.upper()
    if normalized in {"Y", "YES", "TRUE", "1", "T"}:
        return True
    if normalized in {"N", "NO", "FALSE", "0", "F"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def normalize_airport_code(value: str) -> str:
    code = value.strip().upper()
    if len(code) != 3 or not code.isalnum():
        raise ValueError(f"airport code must be a 3-character IATA code: {value!r}")
    return code


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
