"""krairport 명령줄 진입점."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from krairport.client import KrairportClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="krairport")
    subparsers = parser.add_subparsers(dest="command", required=True)

    departures = subparsers.add_parser("departures")
    _add_flight_args(departures)

    arrivals = subparsers.add_parser("arrivals")
    _add_flight_args(arrivals)

    parking = subparsers.add_parser("parking-status")
    parking.add_argument("--airport-code", required=True)

    args = parser.parse_args(argv)
    client = KrairportClient.from_env()

    result: Any
    if args.command == "departures":
        result = client.departures(
            airport_code=args.airport_code,
            searchday=args.searchday,
            from_time=args.from_time,
            to_time=args.to_time,
            flight_id=args.flight_id,
        )
    elif args.command == "arrivals":
        result = client.arrivals(
            airport_code=args.airport_code,
            searchday=args.searchday,
            from_time=args.from_time,
            to_time=args.to_time,
            flight_id=args.flight_id,
        )
    else:
        result = client.parking_status(airport_code=args.airport_code)

    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0


def _add_flight_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--airport-code", required=True)
    parser.add_argument("--searchday")
    parser.add_argument("--from-time")
    parser.add_argument("--to-time")
    parser.add_argument("--flight-id")


def _jsonable(value: Any) -> Any:
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
