"""IIAC 공개 원문의 0 밀리초를 허용하되 시각 정밀도를 버려 승인하지 않는다."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from krairport import KrairportParseError, parse_parking_snapshot_values

FIXTURE = Path(__file__).parent / "fixtures" / "iiac_parking_fractional_timestamp.json"
KST = timezone(timedelta(hours=9))


@pytest.mark.parametrize(
    "index,expected",
    [
        (0, datetime(2026, 11, 13, 18, 16, 0, tzinfo=KST)),
        (18, datetime(2026, 11, 13, 18, 16, 5, tzinfo=KST)),
    ],
)
def test_observed_iiac_zero_milliseconds_keep_exact_kst_and_original_row(index, expected):
    # 수집된 공개 응답의 첫/마지막 행이며 값이나 datetm을 고쳐 쓰지 않는다.
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw = rows[index]
    original = dict(raw)
    parsed = parse_parking_snapshot_values(raw, provider="iiac")
    assert parsed.observed_at == expected
    assert parsed.observed_at.microsecond == 0
    assert parsed.total_spaces == int(raw["parkingarea"])
    assert parsed.occupied_spaces == int(raw["parking"])
    assert raw == original


def test_all_19_observed_iiac_rows_keep_separate_source_seconds():
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(rows) == 19
    parsed = [parse_parking_snapshot_values(row, provider="iiac") for row in rows]
    assert [value.observed_at.second for value in parsed] == [
        int(row["datetm"][12:14]) for row in rows
    ]
    assert {value.observed_at.date() for value in parsed} == {datetime(2026, 11, 13).date()}
    assert all(value.observed_at.utcoffset() == timedelta(hours=9) for value in parsed)


@pytest.mark.parametrize(
    "timestamp",
    [
        "00000000000000.000",
        "20260000181600.000",
        "20260229181600.000",
        "20261113240000.000",
        "20261113186000.000",
        "20261113181660.000",
        "20261113181600.001",
        "20261113181600.123",
        "20261113181600.0",
        "20261113181600.00",
        "20261113181600.0000",
        "20261113181600.",
        "202611131816.000",
        "20261113.000",
        "2026-11-13 18:16:00.000",
        "20261113181600.000e0",
        "prefix20261113181600.000",
        "20261113181600.000suffix",
    ],
)
def test_invalid_or_unobserved_fractional_formats_stay_sanitized_errors(timestamp):
    with pytest.raises(KrairportParseError, match="timestamp") as caught:
        parse_parking_snapshot_values(
            {"parkingarea": "640", "parking": "0", "datetm": timestamp}, provider="iiac"
        )
    assert timestamp not in str(caught.value)


@pytest.mark.parametrize(
    "timestamp,expected",
    [
        ("20240229000000.000", datetime(2024, 2, 29, tzinfo=KST)),
        ("20260519222836.000", datetime(2026, 5, 19, 22, 28, 36, tzinfo=KST)),
    ],
)
def test_historical_zero_milliseconds_are_not_replaced_with_current_time(timestamp, expected):
    value = parse_parking_snapshot_values(
        {"parkingarea": "640", "parking": "0", "datetm": timestamp},
        provider="iiac",
    )
    assert value.observed_at == expected
    assert value.total_spaces == 640 and value.occupied_spaces == 0
