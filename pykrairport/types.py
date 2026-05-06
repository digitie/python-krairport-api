"""Public typing aliases for pykrairport integrations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeAlias

from pykrairport.enums import Airport, Direction, Provider

ProviderCode: TypeAlias = Literal["kac", "iiac"]
DirectionCode: TypeAlias = Literal["arrival", "departure"]
AirportCodeText: TypeAlias = str

ProviderLike: TypeAlias = Provider | ProviderCode | str
DirectionLike: TypeAlias = Direction | DirectionCode | str
AirportCodeLike: TypeAlias = Airport | AirportCodeText

RawRecord: TypeAlias = Mapping[str, Any]
CoordinateTuple: TypeAlias = tuple[float, float]
GeoJsonPosition: TypeAlias = tuple[float, float]
