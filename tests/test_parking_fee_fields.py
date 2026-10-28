from __future__ import annotations

from xml.sax.saxutils import escape

import pytest

from krairport.exceptions import KrairportParseError
from krairport.models import ParkingFee
from krairport.providers.kac import KacClient
from tests.conftest import FakeResponse, FakeSession


async def _read(fields: dict[str, str]) -> ParkingFee:
    item = "".join(f"<{key}>{escape(value)}</{key}>" for key, value in fields.items())
    xml = (
        "<response><header><resultCode>00</resultCode></header><body><items><item>"
        f"{item}</item></items></body></response>"
    )
    client = KacClient("OFFLINE_KEY", session=FakeSession([FakeResponse(text=xml)]), retries=0)
    return (await client.parking_fees(airport_code="GMP"))[0]


async def test_fee_official_fields_and_vehicle_holiday_types_are_preserved() -> None:
    fields = {
        "siteName": "김포국제공항",
        "parkingParkingName": "국제선 주차장",
        "parkingName": "과거 별칭",
    }
    expected: dict[str, int] = {}
    for vehicle, suffix in (("small", ""), ("large", "d")):
        for holiday, provider_prefix in (("", "parking"), ("holiday_", "parkingHoli")):
            for name, source, value in (
                ("basic_minutes", "BasicM", 30),
                ("basic_fee", "BasicAccount", 1000),
                ("free_minutes", "FreeM", 0),
                ("unit_minutes", "MinuteM", 15),
                ("unit_fee", "MinuteAccount", 500),
                ("daily_max_fee", "MaxAccount", 20000),
            ):
                fields[provider_prefix + source + suffix] = f"{value:,}"
                expected[f"{vehicle}_{holiday}{name}"] = value
    fields["parkingDayMaxAccount"] = "99999"
    result = await _read(fields)
    assert result.airport_code == "GMP"
    assert result.airport_name == "김포국제공항"
    assert result.parking_name == "국제선 주차장"
    for name, value in expected.items():
        assert getattr(result, name) == value
    assert result.raw == fields
    assert ParkingFee.model_validate(result.model_dump(mode="json")) == result


async def test_missing_fees_remain_none_and_zero_is_not_replaced_by_alias() -> None:
    result = await _read(
        {
            "parkingParkingName": "",
            "parkingName": "과거 주차장",
            "parkingMaxAccount": "0",
            "parkingDayMaxAccount": "20000",
            "parkingHoliBasicAccount": "-",
            "parkingHoliMinuteM": " ",
        }
    )
    assert result.parking_name == "과거 주차장"
    assert result.small_daily_max_fee == 0
    assert result.small_holiday_basic_fee is None
    assert result.small_holiday_unit_minutes is None
    assert result.large_holiday_daily_max_fee is None


@pytest.mark.parametrize("value", ["1.5", "-1", "NaN", "Infinity", "invalid"])
async def test_invalid_fee_is_not_truncated_or_fabricated(value: str) -> None:
    with pytest.raises(KrairportParseError):
        await _read({"parkingHoliMinuteAccount": value})


async def test_old_public_constructor_remains_compatible() -> None:
    result = ParkingFee(
        airport_code="GMP",
        parking_name=None,
        small_basic_minutes=None,
        small_basic_fee=None,
        large_basic_minutes=None,
        large_basic_fee=None,
        small_daily_max_fee=None,
        large_daily_max_fee=None,
    )
    assert result.small_holiday_basic_fee is None
    assert result.airport_name is None


@pytest.mark.parametrize("value", ["1,5", ",1000", "1,,000", "1,000,", "0,000", "1234,000"])
async def test_malformed_thousands_separator_is_missing_not_a_guessed_fee(value: str) -> None:
    result = await _read({"parkingMaxAccount": value, "parkingDayMaxAccount": "20000"})
    assert result.small_daily_max_fee is None
    assert result.raw["parkingMaxAccount"] == value


@pytest.mark.parametrize("value,expected", [("1,000", 1000), ("12,345,678", 12345678), ("000", 0)])
async def test_valid_thousands_and_unseparated_integer_are_preserved(
    value: str, expected: int,
) -> None:
    assert (await _read({"parkingMinuteAccount": value})).small_unit_fee == expected
