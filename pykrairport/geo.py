"""지리 좌표 정규화 도우미."""

from __future__ import annotations

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from pykrairport.enums import CoordinateDatum
from pykrairport.types import CoordinateTuple, GeoJsonPosition, RawRecord

CoordinateKind = Literal["latitude", "longitude"]
_HEMISPHERE_SIGNS = {"N": 1, "E": 1, "S": -1, "W": -1}
_HEMISPHERE_WORDS = {"NORTH": "N", "EAST": "E", "SOUTH": "S", "WEST": "W"}
_HEMISPHERE_LETTER_RE = re.compile(r"(?<![A-Z])([NSEW])(?![A-Z])")
_NUMBER_RE = re.compile(r"[+-]?\d+(?:\.\d+)?")
_MISSING = object()


class Coordinate(BaseModel):
    """WGS84 decimal degrees 좌표.

    `latitude`와 `longitude`는 항상 decimal degrees입니다. 소비자가
    `[longitude, latitude]` 순서를 기대하면 `as_geojson_position()`을 사용합니다.
    """

    model_config = ConfigDict(frozen=True)

    latitude: float
    longitude: float
    datum: CoordinateDatum = CoordinateDatum.WGS84

    def __init__(
        self,
        latitude: Any = _MISSING,
        longitude: Any = _MISSING,
        **data: Any,
    ) -> None:
        if latitude is not _MISSING:
            if "latitude" in data:
                raise TypeError("latitude was provided both positionally and by keyword")
            data["latitude"] = latitude
        if longitude is not _MISSING:
            if "longitude" in data:
                raise TypeError("longitude was provided both positionally and by keyword")
            data["longitude"] = longitude
        super().__init__(**data)

    @field_validator("latitude")
    @classmethod
    def _validate_latitude(cls, value: float) -> float:
        return _validate_decimal_degrees(value, kind="latitude")

    @field_validator("longitude")
    @classmethod
    def _validate_longitude(cls, value: float) -> float:
        return _validate_decimal_degrees(value, kind="longitude")

    @classmethod
    def from_values(cls, latitude: Any, longitude: Any) -> Coordinate:
        """decimal 또는 DMS 유사 위경도 값으로 좌표를 만듭니다."""

        return cls(
            latitude=to_decimal_degrees(latitude, kind="latitude"),
            longitude=to_decimal_degrees(longitude, kind="longitude"),
        )

    @classmethod
    def from_mapping(
        cls,
        record: RawRecord,
        *,
        latitude_keys: tuple[str, ...] = ("latitude", "lat", "latitude_deg", "y"),
        longitude_keys: tuple[str, ...] = ("longitude", "lon", "lng", "longitude_deg", "x"),
    ) -> Coordinate | None:
        """공급자가 자주 쓰는 위경도 필드명에서 좌표를 만듭니다."""

        latitude = _first_present(record, latitude_keys)
        longitude = _first_present(record, longitude_keys)
        if latitude is None or longitude is None:
            return None
        return cls.from_values(latitude, longitude)

    def as_tuple(self) -> CoordinateTuple:
        """사람이 읽거나 거리 계산에 쓰기 좋은 `(latitude, longitude)`를 반환합니다."""

        return (self.latitude, self.longitude)

    def as_geojson_position(self) -> GeoJsonPosition:
        """GeoJSON 호환 소비자를 위한 `(longitude, latitude)`를 반환합니다."""

        return (self.longitude, self.latitude)

    def distance_to_km(self, other: Coordinate) -> float:
        """다른 좌표까지의 대권 거리를 킬로미터 단위로 반환합니다."""

        radius_km = 6371.0088
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        dlat = lat2 - lat1
        dlon = math.radians(other.longitude - self.longitude)
        haversine = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        return 2 * radius_km * math.asin(math.sqrt(haversine))


def to_decimal_degrees(value: Any, *, kind: CoordinateKind | None = None) -> float:
    """decimal 또는 DMS 유사 좌표 값을 decimal degrees로 정규화합니다."""

    text = _strip_coordinate_text(value)
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

    if _strip_coordinate_text(value) is None:
        return None
    return to_decimal_degrees(value, kind=kind)


def coordinate_from_mapping(record: RawRecord) -> Coordinate | None:
    """일반적인 lat/lon key를 가진 mapping에서 WGS84 좌표를 반환합니다."""

    return Coordinate.from_mapping(record)


def _strip_coordinate_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "-"}:
        return None
    return text


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


def _validate_decimal_degrees(
    value: float,
    *,
    kind: CoordinateKind | None,
) -> float:
    if not math.isfinite(value):
        raise ValueError(f"coordinate must be finite: {value!r}")
    if kind == "latitude" and not -90 <= value <= 90:
        raise ValueError(f"latitude out of range: {value!r}")
    if kind == "longitude" and not -180 <= value <= 180:
        raise ValueError(f"longitude out of range: {value!r}")
    if kind is None and not -180 <= value <= 180:
        raise ValueError(f"coordinate out of range: {value!r}")
    return value


def _first_present(record: RawRecord, keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = record.get(key)
        if _strip_coordinate_text(value) is not None:
            return value
    return None
