from __future__ import annotations

import pytest

from pykrairport._convert import (
    as_list,
    first_value,
    normalize_airport_code,
    strip_or_none,
    to_bool_or_none,
    to_float_or_none,
    to_int_or_none,
)


def test_strip_or_none_normalizes_empty_values() -> None:
    assert strip_or_none(None) is None
    assert strip_or_none(" ") is None
    assert strip_or_none("-") is None
    assert strip_or_none(" GMP ") == "GMP"


def test_first_value_skips_empty_values() -> None:
    assert first_value({"a": " ", "b": "value"}, "a", "b") == "value"
    assert first_value({"a": " "}, "a", "missing") is None


def test_numeric_conversions() -> None:
    assert to_int_or_none("1,234") == 1234
    assert to_int_or_none("") is None
    assert to_float_or_none("+12.5") == 12.5
    assert to_float_or_none(None) is None


def test_bad_numeric_conversions_raise() -> None:
    with pytest.raises(ValueError):
        to_int_or_none("bad")
    with pytest.raises(ValueError):
        to_float_or_none("bad")


def test_bool_conversion() -> None:
    assert to_bool_or_none("Y") is True
    assert to_bool_or_none("false") is False
    assert to_bool_or_none(" ") is None
    with pytest.raises(ValueError):
        to_bool_or_none("maybe")


def test_airport_code_validation() -> None:
    assert normalize_airport_code(" icn ") == "ICN"
    with pytest.raises(ValueError):
        normalize_airport_code("INCHEON")


def test_as_list() -> None:
    assert as_list(None) == []
    assert as_list([1, 2]) == [1, 2]
    assert as_list("x") == ["x"]
