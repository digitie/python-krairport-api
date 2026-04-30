from __future__ import annotations

from pykrairport.cli import main
from pykrairport.models import Flight, ParkingAreaStatus


class FakeClient:
    @classmethod
    def from_env(cls):  # type: ignore[no-untyped-def]
        return cls()

    def departures(self, **kwargs):  # type: ignore[no-untyped-def]
        return [_flight("departure")]

    def arrivals(self, **kwargs):  # type: ignore[no-untyped-def]
        return [_flight("arrival")]

    def parking_status(self, **kwargs):  # type: ignore[no-untyped-def]
        return [
            ParkingAreaStatus(
                airport_code="ICN",
                terminal="T1",
                parking_area="short",
                occupied=1,
                capacity=2,
                updated_at=None,
                raw={},
            )
        ]


def test_cli_departures(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("pykrairport.cli.KrairportClient", FakeClient)

    assert main(["departures", "--airport-code", "GMP"]) == 0

    assert '"direction": "departure"' in capsys.readouterr().out


def test_cli_arrivals(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("pykrairport.cli.KrairportClient", FakeClient)

    assert main(["arrivals", "--airport-code", "ICN"]) == 0

    assert '"direction": "arrival"' in capsys.readouterr().out


def test_cli_parking_status(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("pykrairport.cli.KrairportClient", FakeClient)

    assert main(["parking-status"]) == 0

    assert '"occupied": 1' in capsys.readouterr().out


def _flight(direction: str) -> Flight:
    return Flight(
        provider="kac" if direction == "departure" else "iiac",
        airport_code="GMP" if direction == "departure" else "ICN",
        flight_id="KE1",
        flight_unique_id=None,
        direction="departure" if direction == "departure" else "arrival",
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
        raw={},
    )
