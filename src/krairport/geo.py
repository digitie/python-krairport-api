"""공항 API에서 쓰는 WGS84 좌표와 주소 문자열 도우미."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any, Literal, TypeAlias

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from krairport._convert import first_value, strip_or_none, to_float_or_none

CoordinateKind: TypeAlias = Literal["latitude", "longitude"]
CoordinateTuple: TypeAlias = tuple[float, float]
GeoJsonPosition: TypeAlias = tuple[float, float]

_HEMISPHERE_SIGNS = {"N": 1, "E": 1, "S": -1, "W": -1}
_HEMISPHERE_WORDS = {"NORTH": "N", "EAST": "E", "SOUTH": "S", "WEST": "W"}
_HEMISPHERE_LETTER_RE = re.compile(r"(?<![A-Z])([NSEW])(?![A-Z])")
_NUMBER_RE = re.compile(r"[+-]?\d+(?:\.\d+)?")


class Coordinate(BaseModel):
    """WGS84 decimal degrees 좌표.

    public 축 순서는 사람이 읽는 `(latitude, longitude)`입니다. GeoJSON이 필요할 때만
    `as_geojson_position()`으로 `(longitude, latitude)`를 명시합니다.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    lat: float = Field(
        validation_alias=AliasChoices(
            "lat",
            "latitude",
            "mapY",
            "map_y",
            "mapy",
            "y",
            "yValue",
            "lcLatitude",
            "위도",
        )
    )
    lon: float = Field(
        validation_alias=AliasChoices(
            "lon",
            "lng",
            "longitude",
            "mapX",
            "map_x",
            "mapx",
            "x",
            "xValue",
            "lcLongitude",
            "경도",
        )
    )
    altitude_m: float | None = None
    accuracy_m: float | None = None
    srid: int = 4326

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def _coerce_axis(cls, value: Any) -> float:
        number = to_decimal_degrees(value)
        if not math.isfinite(number):
            raise ValueError(f"coordinate must be finite: {value!r}")
        return number

    @field_validator("altitude_m", "accuracy_m", mode="before")
    @classmethod
    def _coerce_optional_float(cls, value: Any) -> float | None:
        return to_float_or_none(value)

    @field_validator("srid")
    @classmethod
    def _validate_srid(cls, value: int) -> int:
        if int(value) != 4326:
            raise ValueError("Coordinate stores only WGS84 EPSG:4326 values")
        return int(value)

    def model_post_init(self, __context: Any) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError("lat must be between -90 and 90")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError("lon must be between -180 and 180")
        if self.accuracy_m is not None and self.accuracy_m < 0:
            raise ValueError("accuracy_m must be greater than or equal to 0")

    @property
    def latitude(self) -> float:
        return self.lat

    @property
    def longitude(self) -> float:
        return self.lon

    @classmethod
    def from_values(cls, latitude: Any, longitude: Any) -> Coordinate:
        """decimal 또는 DMS 유사 위도/경도 값으로 좌표를 만듭니다."""

        return cls(
            lat=round(to_decimal_degrees(latitude, kind="latitude"), 12),
            lon=round(to_decimal_degrees(longitude, kind="longitude"), 12),
        )

    @classmethod
    def from_tuple(
        cls,
        value: tuple[float, float],
        *,
        order: Literal["lat_lon", "lon_lat"] = "lat_lon",
    ) -> Coordinate:
        """2개 원소 tuple을 좌표로 변환합니다."""

        if len(value) != 2:
            raise ValueError("coordinate tuple must contain exactly two values")
        first, second = value
        if order == "lon_lat":
            return cls.from_values(second, first)
        return cls.from_values(first, second)

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> Coordinate | None:
        """provider row에서 흔한 위경도 key를 찾아 좌표를 반환합니다."""

        lon_value = first_value(
            row,
            "lon",
            "lng",
            "longitude",
            "mapX",
            "map_x",
            "mapx",
            "x",
            "xValue",
            "lcLongitude",
            "경도",
        )
        lat_value = first_value(
            row,
            "lat",
            "latitude",
            "mapY",
            "map_y",
            "mapy",
            "y",
            "yValue",
            "lcLatitude",
            "위도",
        )
        if lon_value is None or lat_value is None:
            return None
        if _is_missing_coordinate(lon_value, kind="longitude") or _is_missing_coordinate(
            lat_value,
            kind="latitude",
        ):
            return None
        return cls(
            lat=lat_value,
            lon=lon_value,
            altitude_m=first_value(row, "altitude_m", "altitude", "고도"),
            accuracy_m=first_value(row, "accuracy_m", "accuracy", "정확도"),
        )

    def as_tuple(self) -> CoordinateTuple:
        """`(latitude, longitude)` 순서로 반환합니다."""

        return self.lat, self.lon

    def as_lat_lon(self) -> CoordinateTuple:
        """`(latitude, longitude)` 순서 명시 alias입니다."""

        return self.as_tuple()

    def as_lon_lat(self) -> GeoJsonPosition:
        """`(longitude, latitude)` 순서로 반환합니다."""

        return self.lon, self.lat

    def as_geojson_position(self) -> GeoJsonPosition:
        """GeoJSON Position 규칙의 `(longitude, latitude)`를 반환합니다."""

        return self.as_lon_lat()

    def distance_to_m(self, other: Coordinate) -> float:
        """다른 WGS84 좌표까지의 대권 거리를 미터 단위로 반환합니다."""

        radius_m = 6371008.8
        lat1 = math.radians(self.lat)
        lat2 = math.radians(other.lat)
        dlat = lat2 - lat1
        dlon = math.radians(other.lon - self.lon)
        haversine = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        return 2 * radius_m * math.asin(math.sqrt(haversine))

    def distance_to_km(self, other: Coordinate) -> float:
        """다른 WGS84 좌표까지의 대권 거리를 킬로미터 단위로 반환합니다."""

        return self.distance_to_m(other) / 1000.0


def coerce_coordinate(value: Coordinate | CoordinateTuple) -> Coordinate:
    """좌표 모델 또는 `(latitude, longitude)` tuple을 `Coordinate`로 변환합니다."""

    if isinstance(value, Coordinate):
        return value
    return Coordinate.from_tuple(value)


def address_from_mapping(row: Mapping[str, Any]) -> str | None:
    """provider row에서 주소 계열 필드를 찾아 문자열로 반환합니다."""

    return strip_or_none(
        first_value(
            row,
            "address",
            "addr",
            "address1",
            "address2",
            "roadAddress",
            "roadAddr",
            "jibunAddress",
            "jibunAddr",
            "주소",
        )
    )


def to_decimal_degrees(value: Any, *, kind: CoordinateKind | None = None) -> float:
    """decimal 또는 DMS 유사 좌표 값을 decimal degrees로 정규화합니다."""

    text = strip_or_none(value)
    if text is None:
        raise ValueError("coordinate value is empty")

    normalized = text.upper().replace("º", "°")
    hemisphere = _extract_hemisphere(normalized)
    numbers = [float(part) for part in _NUMBER_RE.findall(normalized)]
    if not numbers:
        raise ValueError(f"invalid coordinate value: {value!r}")

    degrees = numbers[0]
    minutes = numbers[1] if len(numbers) >= 2 else 0.0
    seconds = numbers[2] if len(numbers) >= 3 else 0.0
    if minutes < 0 or seconds < 0 or minutes >= 60 or seconds >= 60:
        raise ValueError(f"invalid coordinate minutes/seconds: {value!r}")

    sign = -1 if degrees < 0 else 1
    if hemisphere is not None:
        hemisphere_sign = _HEMISPHERE_SIGNS[hemisphere]
        if degrees < 0 and hemisphere_sign > 0:
            raise ValueError(f"conflicting coordinate sign and hemisphere: {value!r}")
        sign = hemisphere_sign

    decimal = sign * (abs(degrees) + minutes / 60 + seconds / 3600)
    return _validate_decimal_degrees(decimal, kind=kind)


def to_decimal_degrees_or_none(
    value: Any,
    *,
    kind: CoordinateKind | None = None,
) -> float | None:
    """빈 좌표 값이면 `None`, 값이 있으면 decimal degrees를 반환합니다."""

    if strip_or_none(value) is None:
        return None
    return to_decimal_degrees(value, kind=kind)


def _validate_decimal_degrees(value: float, *, kind: CoordinateKind | None) -> float:
    if not math.isfinite(value):
        raise ValueError(f"coordinate must be finite: {value!r}")
    if kind == "latitude" and not -90 <= value <= 90:
        raise ValueError(f"latitude out of range: {value!r}")
    if kind == "longitude" and not -180 <= value <= 180:
        raise ValueError(f"longitude out of range: {value!r}")
    if kind is None and not -180 <= value <= 180:
        raise ValueError(f"coordinate out of range: {value!r}")
    return value


def _is_missing_coordinate(value: Any, *, kind: CoordinateKind) -> bool:
    number = to_float_or_none(value)
    if number is None:
        return False
    if kind == "latitude":
        return number <= -99.0
    return number <= -180.0


def _extract_hemisphere(value: str) -> str | None:
    hemispheres = [
        hemisphere
        for word, hemisphere in _HEMISPHERE_WORDS.items()
        if re.search(rf"\b{word}\b", value)
    ]
    hemispheres.extend(_HEMISPHERE_LETTER_RE.findall(value))
    if not hemispheres:
        return None
    unique = set(hemispheres)
    if len(unique) > 1:
        raise ValueError(f"coordinate has multiple hemispheres: {value!r}")
    return hemispheres[0]
