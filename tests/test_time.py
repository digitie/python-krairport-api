from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from krairport._time import KST, combine_date_time, parse_kst_datetime


def test_parse_yyyymmddhhmm_as_kst() -> None:
    dt = parse_kst_datetime("202604300610")

    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.day == 30
    assert dt.hour == 6
    assert dt.minute == 10
    assert dt.tzinfo == KST


def test_parse_none_date_and_datetime_inputs() -> None:
    assert parse_kst_datetime(None) is None

    from_date = parse_kst_datetime(date(2026, 4, 30))
    assert from_date is not None
    assert from_date.isoformat() == "2026-04-30T00:00:00+09:00"

    naive = parse_kst_datetime(datetime(2026, 4, 30, 8, 0))
    assert naive is not None
    assert naive.isoformat() == "2026-04-30T08:00:00+09:00"

    aware = parse_kst_datetime(datetime(2026, 4, 29, 23, 0, tzinfo=UTC))
    assert aware is not None
    assert aware.isoformat() == "2026-04-30T08:00:00+09:00"


def test_parse_scientific_timestamp() -> None:
    dt = parse_kst_datetime("2.02604300610E+11")

    assert dt is not None
    assert dt.isoformat() == "2026-04-30T06:10:00+09:00"


def test_parse_fractional_seconds_timestamp() -> None:
    dt = parse_kst_datetime("20260519222836.000")

    assert dt is not None
    assert dt.isoformat() == "2026-05-19T22:28:36+09:00"


def test_combine_2400_rolls_to_next_day() -> None:
    dt = combine_date_time(date(2026, 4, 30), "2400")

    assert dt is not None
    assert dt.isoformat() == "2026-05-01T00:00:00+09:00"


def test_parse_time_with_base_date() -> None:
    dt = parse_kst_datetime("123045", base_date="20260430")

    assert dt is not None
    assert dt.isoformat() == "2026-04-30T12:30:45+09:00"


def test_invalid_base_date_and_24_hour_time_raise() -> None:
    with pytest.raises(ValueError):
        parse_kst_datetime("1200", base_date="2026-04")
    with pytest.raises(ValueError):
        combine_date_time("20260430", "2460")


def test_invalid_timestamp_raises() -> None:
    with pytest.raises(ValueError):
        parse_kst_datetime("not-a-time")
