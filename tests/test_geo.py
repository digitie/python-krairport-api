from __future__ import annotations

import pytest
from kraddr.base import (
    PlaceCoordinate,
    to_decimal_degrees,
    to_decimal_degrees_or_none,
)


def test_place_coordinate_normalizes_decimal_and_geojson_order() -> None:
    coordinate = PlaceCoordinate.from_values("126.450996", "37.469101")

    assert coordinate.latitude == 37.469101
    assert coordinate.longitude == 126.450996
    assert coordinate.as_tuple() == (126.450996, 37.469101)
    assert coordinate.as_lat_lon() == (37.469101, 126.450996)
    assert coordinate.as_geojson_position() == (126.450996, 37.469101)


def test_coordinate_parses_dms_and_hemisphere() -> None:
    latitude = to_decimal_degrees("34° 45' 36\" N", kind="latitude")
    longitude = to_decimal_degrees("126° 22' 49\" E", kind="longitude")
    word_longitude = to_decimal_degrees("126.38027777 East", kind="longitude")

    assert latitude == pytest.approx(34.76)
    assert longitude == pytest.approx(126.38027777777778)
    assert word_longitude == pytest.approx(126.38027777)


def test_coordinate_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        PlaceCoordinate.from_values("126", "91")
    with pytest.raises(ValueError):
        PlaceCoordinate.from_values("181", "37")
    with pytest.raises(ValueError):
        to_decimal_degrees("-37 N", kind="latitude")


def test_coordinate_from_mapping_common_keys() -> None:
    coordinate = PlaceCoordinate.from_mapping({"lat": "35.1", "lng": "128.1"})

    assert coordinate is not None
    assert coordinate.latitude == 35.1
    assert coordinate.longitude == 128.1
    assert PlaceCoordinate.from_mapping({}) is None
    assert to_decimal_degrees_or_none(" ") is None


def test_coordinate_distance() -> None:
    gimpo = PlaceCoordinate.from_values(126.791, 37.5583)
    incheon = PlaceCoordinate.from_values(126.450996, 37.469101)

    assert gimpo.distance_to_km(incheon) == pytest.approx(31.6, abs=1.0)
