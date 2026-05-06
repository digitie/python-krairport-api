"""Public response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pykrairport.enums import AirportType, Direction, Provider
from pykrairport.geo import Coordinate
from pykrairport.types import RawRecord


@dataclass(frozen=True, slots=True)
class Flight:
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
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class AircraftAssignment:
    airport_code: str
    flight_id: str
    flight_unique_id: str | None
    aircraft_registration: str | None
    aircraft_type: str | None
    airline_name: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    gate: str | None
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class ParkingFee:
    airport_code: str
    parking_name: str | None
    small_basic_minutes: int | None
    small_basic_fee: int | None
    large_basic_minutes: int | None
    large_basic_fee: int | None
    small_daily_max_fee: int | None
    large_daily_max_fee: int | None
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class ParkingAreaStatus:
    airport_code: str
    terminal: str | None
    parking_area: str
    occupied: int | None
    capacity: int | None
    updated_at: datetime | None
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class ArrivalCongestion:
    terminal: str
    entry_gate: str
    flight_id: str | None
    airport_code: str | None
    gate_number: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    korean_count: int | None
    foreign_count: int | None
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class PassengerForecast:
    display_date: str
    time_range: str
    t1_arrival_east: int | None
    t1_arrival_west: int | None
    t1_departure_total: int | None
    t2_arrival_total: int | None
    t2_departure_total: int | None
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class AirportCode:
    code: str
    korean_name: str | None
    english_name: str | None
    japanese_name: str | None
    chinese_name: str | None
    icao_code: str | None = None
    provider: Provider | None = None
    municipality: str | None = None
    coordinate: Coordinate | None = None
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class FlightSchedule:
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
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class AirportFacility:
    provider: Provider
    airport_code: str | None
    terminal: str | None
    name: str
    category: str | None
    floor: str | None
    location: str | None
    business_hours: str | None
    telephone: str | None
    coordinate: Coordinate | None = None
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class BusRoute:
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
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class TaxiStatus:
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
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class WorldWeather:
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
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class ServiceDestination:
    airport_code: str | None
    airport_name: str | None
    city_code: str | None
    city_name: str | None
    country_name: str | None
    coordinate: Coordinate | None = None
    raw: RawRecord = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class AirportMetadata:
    code: str
    provider: Provider
    name_english: str
    name_korean: str | None = None
    icao_code: str | None = None
    municipality: str | None = None
    country_code: str = "KR"
    timezone: str = "Asia/Seoul"
    coordinate: Coordinate | None = None
    elevation_ft: int | None = None
    airport_type: AirportType = AirportType.UNKNOWN
    active: bool = True
    source: str | None = None
