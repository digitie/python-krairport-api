"""Geographic coordinate normalization helpers."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Literal

from pykrairport.enums import CoordinateDatum
from pykrairport.types import CoordinateTuple, GeoJsonPosition, RawRecord

CoordinateKind = Literal["latitude", "longitude"]
_HEMISPHERE_SIGNS = {"N": 1, "E": 1, "S": -1, "W": -1}
_HEMISPHERE_WORDS = {"NORTH": "N", "EAST": "E", "SOUTH": "S", "WEST": "W"}
_HEMISPHERE_LETTER_RE = re.compile(r"(?<![A-Z])([NSEW])(?![A-Z])")
_NUMBER_RE = re.compile(r"[+-]?\d+(?:\.\d+)?")


@dataclass(frozen=True, slots=True)
class Coordinate:
    """WGS84 coordinate in decimal degrees.

    `latitude` and `longitude` are always decimal degrees. Use
    `as_geojson_position()` when a consumer expects `[longitude, latitude]`.
    """

    latitude: float
    longitude: float
    datum: CoordinateDatum = CoordinateDatum.WGS84

    def __post_init__(self) -> None:
        latitude = _validate_decimal_degrees(float(self.latitude), kind="latitude")
        longitude = _validate_decimal_degrees(float(self.longitude), kind="longitude")
        object.__setattr__(self, "latitude", latitude)
        object.__setattr__(self, "longitude", longitude)
        object.__setattr__(self, "datum", CoordinateDatum(str(self.datum)))

    @classmethod
    def from_values(cls, latitude: Any, longitude: Any) -> Coordinate:
        """Build a coordinate from decimal or DMS-like latitude/longitude values."""

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
        """Build a coordinate from common provider latitude/longitude field names."""

        latitude = _first_present(record, latitude_keys)
        longitude = _first_present(record, longitude_keys)
        if latitude is None or longitude is None:
            return None
        return cls.from_values(latitude, longitude)

    def as_tuple(self) -> CoordinateTuple:
        """Return `(latitude, longitude)` for human-readable/geodesic use."""

        return (self.latitude, self.longitude)

    def as_geojson_position(self) -> GeoJsonPosition:
        """Return `(longitude, latitude)` for GeoJSON-compatible consumers."""

        return (self.longitude, self.latitude)

    def distance_to_km(self, other: Coordinate) -> float:
        """Return great-circle distance to another coordinate in kilometers."""

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
    """Normalize decimal or DMS-like coordinate values to decimal degrees."""

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
    """Return decimal degrees or `None` for empty coordinate values."""

    if _strip_coordinate_text(value) is None:
        return None
    return to_decimal_degrees(value, kind=kind)


def coordinate_from_mapping(record: RawRecord) -> Coordinate | None:
    """Return a WGS84 coordinate from a mapping with common lat/lon keys."""

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
