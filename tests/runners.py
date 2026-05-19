from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeAlias

import krairport.providers.iiac as iiac_provider
import krairport.providers.kac as kac_provider
from krairport._routing import provider_for_airport
from krairport.debug import jsonable
from krairport.enums import Direction, Provider, normalize_direction

FixtureCase: TypeAlias = Mapping[str, Any]
ParsedResult: TypeAlias = Any
ParseFunc: TypeAlias = Callable[[FixtureCase], ParsedResult]
ProcessFunc: TypeAlias = Callable[[ParsedResult, FixtureCase], Any]


def parse_departures(case: FixtureCase) -> Any:
    return _parse_flights(case, Direction.DEPARTURE)


def parse_arrivals(case: FixtureCase) -> Any:
    return _parse_flights(case, Direction.ARRIVAL)


def parse_aircraft_assignments(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    return [
        kac_provider._build_aircraft_assignment(
            row,
            requested_airport_code=_optional_str(input_data.get("airport_code")),
        )
        for row in _rows(case)
    ]


def parse_parking_fees(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    return [
        kac_provider._build_parking_fee(
            row,
            requested_airport_code=_optional_str(input_data.get("airport_code")),
        )
        for row in _rows(case)
    ]


def parse_parking_status(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    airport_code = str(input_data.get("airport_code") or "ICN").upper()
    if provider_for_airport(airport_code) is Provider.IIAC:
        return [iiac_provider._build_parking_status(row) for row in _rows(case)]
    return [
        kac_provider._build_parking_status(row, requested_airport_code=airport_code)
        for row in _rows(case)
    ]


def parse_arrival_congestion(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    return [
        iiac_provider._build_arrival_congestion(
            row,
            terminal_hint=_optional_str(input_data.get("terminal")),
        )
        for row in _rows(case)
    ]


def parse_passenger_forecast(case: FixtureCase) -> Any:
    return [iiac_provider._build_passenger_forecast(row) for row in _rows(case)]


def parse_flight_schedules(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    airport_code = str(input_data.get("airport_code") or "ICN").upper()
    direction = normalize_direction(input_data.get("direction") or Direction.DEPARTURE)
    if provider_for_airport(airport_code) is Provider.IIAC:
        return [
            iiac_provider._build_flight_schedule(row, direction=direction)
            for row in _rows(case)
        ]
    return [
        kac_provider._build_flight_schedule(
            row,
            direction=direction,
            international=bool(input_data.get("international", False)),
        )
        for row in _rows(case)
    ]


def parse_airport_facilities(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    airport_code = str(input_data.get("airport_code") or "ICN").upper()
    if provider_for_airport(airport_code) is Provider.IIAC:
        return [iiac_provider._build_facility(row) for row in _rows(case)]
    return [
        kac_provider._build_airport_facility(row, requested_airport_code=airport_code)
        for row in _rows(case)
    ]


def parse_bus_routes(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    airport_code = str(input_data.get("airport_code") or "ICN").upper()
    if provider_for_airport(airport_code) is Provider.IIAC:
        return [iiac_provider._build_bus_route(row) for row in _rows(case)]
    return [
        kac_provider._build_bus_route(row, provider=Provider.KAC, airport_code=airport_code)
        for row in _rows(case)
    ]


def parse_taxi_status(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    airport_code = str(input_data.get("airport_code") or "ICN").upper()
    if provider_for_airport(airport_code) is Provider.IIAC:
        return [
            iiac_provider._build_taxi_status(
                row,
                terminal_hint=_optional_str(input_data.get("terminal")),
            )
            for row in _rows(case)
        ]
    return [
        kac_provider._build_taxi_status(row, provider=Provider.KAC, airport_code=airport_code)
        for row in _rows(case)
    ]


def parse_world_weather(case: FixtureCase) -> Any:
    input_data = _input_data(case)
    direction = normalize_direction(input_data.get("direction") or Direction.ARRIVAL)
    return [iiac_provider._build_world_weather(row, direction=direction) for row in _rows(case)]


def parse_service_destinations(case: FixtureCase) -> Any:
    return [iiac_provider._build_service_destination(row) for row in _rows(case)]


def parse_raw_items(case: FixtureCase) -> Any:
    return _rows(case)


def process_models(parsed: ParsedResult, case: FixtureCase) -> Any:
    return jsonable(parsed)


RUNNERS: dict[str, dict[str, ParseFunc | ProcessFunc]] = {
    "departures": {"parse": parse_departures, "process": process_models},
    "arrivals": {"parse": parse_arrivals, "process": process_models},
    "aircraft_assignments": {"parse": parse_aircraft_assignments, "process": process_models},
    "parking_fees": {"parse": parse_parking_fees, "process": process_models},
    "parking_status": {"parse": parse_parking_status, "process": process_models},
    "arrival_congestion": {"parse": parse_arrival_congestion, "process": process_models},
    "passenger_forecast": {"parse": parse_passenger_forecast, "process": process_models},
    "flight_schedules": {"parse": parse_flight_schedules, "process": process_models},
    "airport_facilities": {"parse": parse_airport_facilities, "process": process_models},
    "bus_routes": {"parse": parse_bus_routes, "process": process_models},
    "taxi_status": {"parse": parse_taxi_status, "process": process_models},
    "world_weather": {"parse": parse_world_weather, "process": process_models},
    "service_destinations": {"parse": parse_service_destinations, "process": process_models},
    "kac_raw_items": {"parse": parse_raw_items, "process": process_models},
    "iiac_raw_items": {"parse": parse_raw_items, "process": process_models},
}


def _parse_flights(case: FixtureCase, direction: Direction) -> Any:
    input_data = _input_data(case)
    airport_code = str(input_data.get("airport_code") or "ICN").upper()
    if provider_for_airport(airport_code) is Provider.IIAC:
        return [iiac_provider._build_flight(row, direction=direction) for row in _rows(case)]
    return [
        kac_provider._build_flight(row, airport_code=airport_code, direction=direction)
        for row in _rows(case)
    ]


def _rows(case: FixtureCase) -> list[dict[str, Any]]:
    response = case.get("response", {})
    body = response.get("body", []) if isinstance(response, Mapping) else []
    if isinstance(body, list):
        return [dict(row) for row in body if isinstance(row, Mapping)]
    if isinstance(body, Mapping):
        return [dict(body)]
    return []


def _input_data(case: FixtureCase) -> Mapping[str, Any]:
    input_data = case.get("input", {})
    if isinstance(input_data, Mapping):
        return input_data
    return {}


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
