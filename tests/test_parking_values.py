"""수집 승인 경계는 오류 문자열/잘못된 시각을 0/현재시각으로 바꾸지 않는다."""

import pytest

from krairport import KrairportParseError, parse_parking_snapshot_values

KAC = {
    "parkingFullSpace": "640",
    "parkingIstay": "012",
    "parkingGetdate": "2026-10-23",
    "parkingGettime": "09:10:20",
}
IIAC = {"parkingarea": "640", "parking": "12", "datetm": "2026-10-23 09:10"}


@pytest.mark.parametrize("provider, raw", [("kac", KAC), ("iiac", IIAC)])
async def test_valid_strict_values_are_aware_kst(provider, raw):
    value = parse_parking_snapshot_values(raw, provider=provider)
    assert value.total_spaces == 640 and value.occupied_spaces == 12
    assert value.observed_at.utcoffset().total_seconds() == 9 * 3600
    assert value.observed_at.year == 2026 and value.observed_at.hour == 9


@pytest.mark.parametrize(
    "provider,base,key",
    [
        ("kac", KAC, "parkingIstay"),
        ("iiac", IIAC, "parking"),
        ("kac", KAC, "parkingFullSpace"),
        ("iiac", IIAC, "parkingarea"),
    ],
)
@pytest.mark.parametrize(
    "bad",
    [
        "error",
        "",
        None,
        -1,
        True,
        "1.5",
        "1e3",
        "1" * 4301,
        pytest.param(10**5000, id="huge-integer"),
    ],
)
async def test_bad_counts_fail_without_original_payload(provider, base, key, bad):
    with pytest.raises(KrairportParseError, match="parking count"):
        parse_parking_snapshot_values({**base, key: bad}, provider=provider)


@pytest.mark.parametrize(
    "provider,raw",
    [
        ("kac", {**KAC, "parkingGetdate": "bad"}),
        ("kac", {**KAC, "parkingGettime": "error"}),
        ("kac", {**KAC, "parkingGetdate": "2026-02-31"}),
        ("kac", {**KAC, "parkingGettime": "99:00:00"}),
        ("iiac", {**IIAC, "datetm": "bad"}),
        ("iiac", {**IIAC, "datetm": "2026-02-31 09:00"}),
        ("iiac", {**IIAC, "datetm": "error202610230910"}),
        ("iiac", {**IIAC, "datetm": None}),
    ],
)
async def test_bad_or_missing_timestamp_never_uses_now(provider, raw):
    with pytest.raises(KrairportParseError, match="timestamp"):
        parse_parking_snapshot_values(raw, provider=provider)
