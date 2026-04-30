"""Public response models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

RawRecord = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Flight:
    provider: Literal["kac", "iiac"]
    airport_code: str
    flight_id: str
    flight_unique_id: str | None
    direction: Literal["arrival", "departure"]
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
    raw: RawRecord = field(repr=False)


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
    raw: RawRecord = field(repr=False)


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
    raw: RawRecord = field(repr=False)


@dataclass(frozen=True, slots=True)
class ParkingAreaStatus:
    airport_code: str
    terminal: str | None
    parking_area: str
    occupied: int | None
    capacity: int | None
    updated_at: datetime | None
    raw: RawRecord = field(repr=False)


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
    raw: RawRecord = field(repr=False)


@dataclass(frozen=True, slots=True)
class PassengerForecast:
    display_date: str
    time_range: str
    t1_arrival_east: int | None
    t1_arrival_west: int | None
    t1_departure_total: int | None
    t2_arrival_total: int | None
    t2_departure_total: int | None
    raw: RawRecord = field(repr=False)
