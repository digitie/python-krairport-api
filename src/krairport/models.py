"""공개 응답 모델."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime
from typing import Any, Generic, TypeVar

from kraddr.base import Address, PlaceCoordinate
from pydantic import BaseModel, ConfigDict, Field

from krairport.enums import AirportType, Direction, Provider
from krairport.types import RawRecord


class KrairportModel(BaseModel):
    """공개 불변 응답 모델의 기본 클래스."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        """Pydantic v2 직렬화로 JSON에 바로 쓸 수 있는 dict를 반환합니다."""

        return self.model_dump(mode="json")

    def to_json(self) -> str:
        """Pydantic v2 직렬화로 JSON 문자열을 반환합니다."""

        return self.model_dump_json()


T = TypeVar("T")


class PaginatedResult(KrairportModel, Generic[T]):
    """Uniform page container for provider list/search responses."""

    total: int = 0
    page: int = 1
    size: int = 10
    items: list[T] = Field(default_factory=list)

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def extend(self, items: Sequence[T]) -> None:
        self.items.extend(items)


class Flight(KrairportModel):
    provider: Provider
    airport_code: str
    flight_id: str
    flight_unique_id: str | None
    direction: Direction
    airline_name: str | None
    airline_code: str | None
    departure_airport_code: str | None
    arrival_airport_code: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    status_korean: str | None
    status_english: str | None
    terminal: str | None
    gate: str | None
    codeshare: bool | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class AircraftAssignment(KrairportModel):
    airport_code: str
    flight_id: str
    flight_unique_id: str | None
    aircraft_registration: str | None
    aircraft_type: str | None
    airline_name: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    gate: str | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class ParkingFee(KrairportModel):
    airport_code: str
    parking_name: str | None
    small_basic_minutes: int | None
    small_basic_fee: int | None
    large_basic_minutes: int | None
    large_basic_fee: int | None
    small_daily_max_fee: int | None
    large_daily_max_fee: int | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class ParkingAreaStatus(KrairportModel):
    airport_code: str
    terminal: str | None
    parking_area: str
    occupied: int | None
    capacity: int | None
    updated_at: datetime | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class ArrivalCongestion(KrairportModel):
    terminal: str
    entry_gate: str
    flight_id: str | None
    airport_code: str | None
    gate_number: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    korean_count: int | None
    foreign_count: int | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class PassengerForecast(KrairportModel):
    display_date: str
    time_range: str
    t1_arrival_east: int | None
    t1_arrival_west: int | None
    t1_departure_total: int | None
    t2_arrival_total: int | None
    t2_departure_total: int | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class FlightSchedule(KrairportModel):
    provider: Provider
    direction: Direction
    flight_id: str
    airline_code: str | None
    airline_name: str | None
    departure_airport_code: str | None
    arrival_airport_code: str | None
    scheduled_time: str | None
    start_date: str | None
    end_date: str | None
    days: str | None
    season: str | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class AirportFacility(KrairportModel):
    provider: Provider
    airport_code: str | None
    terminal: str | None
    name: str
    category: str | None
    floor: str | None
    location: str | None
    address: Address | None = None
    business_hours: str | None
    telephone: str | None
    coordinate: PlaceCoordinate | None = None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class BusRoute(KrairportModel):
    provider: Provider
    airport_code: str | None
    area: str | None
    bus_number: str
    bus_class: str | None
    operator: str | None
    platform: str | None
    adult_fare: int | None
    route_info: str | None
    first_time_to_airport: str | None
    last_time_to_airport: str | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class TaxiStatus(KrairportModel):
    provider: Provider
    airport_code: str | None
    terminal: str | None
    stand: str | None
    seoul_count: int | None
    incheon_count: int | None
    gyeonggi_count: int | None
    intercity_count: int | None
    deluxe_count: int | None
    jumbo_count: int | None
    updated_at: datetime | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class WorldWeather(KrairportModel):
    direction: Direction
    flight_id: str | None
    airline_name: str | None
    airport_code: str | None
    airport_name: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    terminal: str | None
    weather: str | None
    temperature: float | None
    feels_like: float | None
    humidity: int | None
    wind_speed: float | None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class ServiceDestination(KrairportModel):
    airport_code: str | None
    airport_name: str | None
    city_code: str | None
    city_name: str | None
    country_name: str | None
    coordinate: PlaceCoordinate | None = None
    raw: RawRecord = Field(default_factory=dict, repr=False)


class AirportMetadata(KrairportModel):
    code: str
    provider: Provider
    name_english: str
    name_korean: str | None = None
    icao_code: str | None = None
    municipality: str | None = None
    country_code: str = "KR"
    timezone: str = "Asia/Seoul"
    coordinate: PlaceCoordinate | None = None
    elevation_ft: int | None = None
    airport_type: AirportType = AirportType.UNKNOWN
    active: bool = True
    source: str | None = None
