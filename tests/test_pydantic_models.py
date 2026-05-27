from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from krairport import Coordinate, Flight, KrairportModel


def test_response_models_are_pydantic_models() -> None:
    flight = Flight(
        provider="kac",
        airport_code="GMP",
        flight_id="KE1",
        flight_unique_id=None,
        direction="departure",
        airline_name=None,
        airline_code=None,
        departure_airport_code=None,
        arrival_airport_code=None,
        scheduled_at=None,
        estimated_at=None,
        status_korean=None,
        status_english=None,
        terminal=None,
        gate=None,
        codeshare=None,
    )

    assert isinstance(flight, BaseModel)
    assert isinstance(flight, KrairportModel)
    assert flight.provider == "kac"
    assert flight.direction == "departure"
    assert flight.to_dict()["provider"] == "kac"
    assert '"direction":"departure"' in flight.to_json()


def test_response_models_are_frozen_and_validate_fields() -> None:
    flight = Flight(
        provider="iiac",
        airport_code="ICN",
        flight_id="KE1",
        flight_unique_id=None,
        direction="arrival",
        airline_name=None,
        airline_code=None,
        departure_airport_code=None,
        arrival_airport_code=None,
        scheduled_at=None,
        estimated_at=None,
        status_korean=None,
        status_english=None,
        terminal=None,
        gate=None,
        codeshare=None,
    )

    with pytest.raises(ValidationError):
        flight.flight_id = "KE2"
    with pytest.raises(ValidationError):
        Flight(
            provider="unknown",
            airport_code="ICN",
            flight_id="KE1",
            flight_unique_id=None,
            direction="arrival",
            airline_name=None,
            airline_code=None,
            departure_airport_code=None,
            arrival_airport_code=None,
            scheduled_at=None,
            estimated_at=None,
            status_korean=None,
            status_english=None,
            terminal=None,
            gate=None,
            codeshare=None,
        )


def test_coordinate_is_a_frozen_pydantic_model() -> None:
    coordinate = Coordinate(lat=37.5583, lon=126.791)

    assert isinstance(coordinate, BaseModel)
    assert coordinate.model_dump(mode="json") == {
        "lat": 37.5583,
        "lon": 126.791,
        "altitude_m": None,
        "accuracy_m": None,
        "srid": 4326,
    }
    with pytest.raises(ValidationError):
        coordinate.lat = 1
    with pytest.raises(ValidationError):
        Coordinate(lat=91, lon=126)
