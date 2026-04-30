"""인천국제공항공사(IIAC) provider adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pykrairport._convert import (
    as_list,
    first_value,
    strip_or_none,
    to_bool_or_none,
    to_int_or_none,
)
from pykrairport._http import HttpClient, SessionLike
from pykrairport._routing import ensure_iiac_airport
from pykrairport._time import parse_kst_datetime
from pykrairport.exceptions import KrairportParseError
from pykrairport.models import ArrivalCongestion, Flight, ParkingAreaStatus, PassengerForecast

DETAILED_FLIGHTS_BASE = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsDeOdp"
TODAY_FLIGHTS_BASE = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp"
PARKING_BASE = "http://apis.data.go.kr/B551177/StatusOfParking"
ARRIVAL_CONGESTION_BASE = "http://apis.data.go.kr/B551177/StatusOfArrivalsCongestion"
PASSENGER_FORECAST_BASE = "http://apis.data.go.kr/B551177/PassengerNoticeKR"


class IiacClient:
    """Low-level client for Incheon International Airport Corporation APIs."""

    def __init__(
        self,
        service_key: str | None,
        *,
        session: SessionLike | None = None,
        timeout: float = 10.0,
        retries: int = 3,
    ) -> None:
        self._http = HttpClient(
            service_key,
            session=session,
            timeout=timeout,
            retries=retries,
        )

    def departures(
        self,
        *,
        airport_code: str = "ICN",
        searchday: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        flight_id: str | None = None,
        flight_unique_id: str | None = None,
        airline_code: str | None = None,
        counterpart_airport_code: str | None = None,
        lang: str = "K",
        inqtimechcd: str = "E",
        detailed: bool = True,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> list[Flight]:
        ensure_iiac_airport(airport_code)
        base = DETAILED_FLIGHTS_BASE if detailed else TODAY_FLIGHTS_BASE
        operation = "getPassengerDeparturesDeOdp" if detailed else "getPassengerDeparturesOdp"
        params = {
            "type": "json",
            "searchday": searchday if detailed else None,
            "from_time": from_time,
            "to_time": to_time,
            "airport_code": counterpart_airport_code,
            "f_id": flight_unique_id,
            "flight_id": flight_id,
            "airline": airline_code,
            "lang": lang,
            "inqtimechcd": inqtimechcd,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{base}/{operation}", params)
        return [_build_flight(row, direction="departure") for row in _extract_items(data)]

    def arrivals(
        self,
        *,
        airport_code: str = "ICN",
        searchday: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        flight_id: str | None = None,
        flight_unique_id: str | None = None,
        airline_code: str | None = None,
        counterpart_airport_code: str | None = None,
        lang: str = "K",
        inqtimechcd: str = "E",
        detailed: bool = True,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> list[Flight]:
        ensure_iiac_airport(airport_code)
        base = DETAILED_FLIGHTS_BASE if detailed else TODAY_FLIGHTS_BASE
        operation = "getPassengerArrivalsDeOdp" if detailed else "getPassengerArrivalsOdp"
        params = {
            "type": "json",
            "searchday": searchday if detailed else None,
            "from_time": from_time,
            "to_time": to_time,
            "airport_code": counterpart_airport_code,
            "f_id": flight_unique_id,
            "flight_id": flight_id,
            "airline": airline_code,
            "lang": lang,
            "inqtimechcd": inqtimechcd,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{base}/{operation}", params)
        return [_build_flight(row, direction="arrival") for row in _extract_items(data)]

    def parking_status(
        self,
        *,
        airport_code: str = "ICN",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ParkingAreaStatus]:
        ensure_iiac_airport(airport_code)
        params = {"type": "json", "pageNo": page_no, "numOfRows": num_of_rows}
        data = self._http.get_json(f"{PARKING_BASE}/getTrackingParking", params)
        return [_build_parking_status(row) for row in _extract_items(data)]

    def arrival_congestion(
        self,
        *,
        airport_code: str = "ICN",
        terminal: str | None = None,
        airport: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ArrivalCongestion]:
        ensure_iiac_airport(airport_code)
        params = {
            "type": "json",
            "terno": terminal,
            "airport": airport,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{ARRIVAL_CONGESTION_BASE}/getArrivalsCongestion", params)
        return [
            _build_arrival_congestion(row, terminal_hint=terminal)
            for row in _extract_items(data)
        ]

    def passenger_forecast(
        self,
        *,
        airport_code: str = "ICN",
        selectdate: int = 0,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[PassengerForecast]:
        ensure_iiac_airport(airport_code)
        params = {
            "type": "json",
            "selectdate": str(selectdate),
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{PASSENGER_FORECAST_BASE}/getfPassengerNoticeIKR", params)
        return [_build_passenger_forecast(row) for row in _extract_items(data)]


def _extract_items(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    response = data.get("response", data)
    if not isinstance(response, Mapping):
        raise KrairportParseError("JSON response does not contain a response object")
    body = response.get("body", response)
    if not isinstance(body, Mapping):
        return []
    items = body.get("items")
    if items is None:
        return []
    if isinstance(items, Mapping):
        candidates = as_list(items.get("item"))
    else:
        candidates = as_list(items)

    rows: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            raise KrairportParseError("JSON item is not an object")
        rows.append(item)
    return rows


def _build_flight(row: Mapping[str, Any], *, direction: str) -> Flight:
    try:
        flight_id = str(first_value(row, "flightId", "flight_id", "airFln", "airfln") or "")
        return Flight(
            provider="iiac",
            airport_code="ICN",
            flight_id=flight_id,
            flight_unique_id=strip_or_none(first_value(row, "f_id", "fid", "ufid")),
            direction="departure" if direction == "departure" else "arrival",
            airline_name=strip_or_none(
                first_value(row, "airline", "airlineKorean", "airlineEnglish", "airlineNm")
            ),
            airline_code=strip_or_none(first_value(row, "airlineCode", "airline")),
            departure_airport_code=strip_or_none(
                first_value(row, "airport", "departureAirportCode", "depAirportCode")
            ),
            arrival_airport_code=strip_or_none(
                first_value(row, "arrivedKor", "arrAirportCode", "destinationAirportCode")
            ),
            scheduled_at=parse_kst_datetime(
                first_value(row, "scheduleDateTime", "scheduledatetime", "scheduletime")
            ),
            estimated_at=parse_kst_datetime(
                first_value(row, "estimatedDateTime", "estimateddatetime", "estimatedtime")
            ),
            status_korean=strip_or_none(first_value(row, "remarkKor", "rmkKor", "statusKor")),
            status_english=strip_or_none(first_value(row, "remarkEng", "rmkEng", "statusEng")),
            terminal=strip_or_none(first_value(row, "terminalid", "terminalId", "terminal")),
            gate=strip_or_none(first_value(row, "gatenumber", "gateNumber", "gate")),
            codeshare=to_bool_or_none(first_value(row, "codeshare", "cdsrYn")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse IIAC flight record: {exc}") from exc


def _build_parking_status(row: Mapping[str, Any]) -> ParkingAreaStatus:
    try:
        return ParkingAreaStatus(
            airport_code="ICN",
            terminal=strip_or_none(first_value(row, "terminal", "terminalid", "terno")),
            parking_area=str(
                first_value(row, "parking", "parkingArea", "floor", "parkingName") or ""
            ),
            occupied=to_int_or_none(first_value(row, "parkingIstay", "occupied", "parkingCount")),
            capacity=to_int_or_none(first_value(row, "parkingFullSpace", "capacity", "totalCount")),
            updated_at=parse_kst_datetime(first_value(row, "datetm", "updatedAt", "sysGetdate")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse IIAC parking status record: {exc}") from exc


def _build_arrival_congestion(
    row: Mapping[str, Any], *, terminal_hint: str | None
) -> ArrivalCongestion:
    try:
        return ArrivalCongestion(
            terminal=str(
                first_value(row, "terno", "terminal", "terminalid") or terminal_hint or ""
            ),
            entry_gate=str(first_value(row, "entrygate", "entryGate", "gatearea", "gate") or ""),
            flight_id=strip_or_none(first_value(row, "flightid", "flight_id", "flightId")),
            airport_code=strip_or_none(first_value(row, "airport", "airportcode", "airportCode")),
            gate_number=strip_or_none(first_value(row, "gatenumber", "gateNumber")),
            scheduled_at=parse_kst_datetime(
                first_value(row, "scheduleDateTime", "scheduledatetime", "scheduletime")
            ),
            estimated_at=parse_kst_datetime(
                first_value(row, "estimatedDateTime", "estimateddatetime", "estimatedtime")
            ),
            korean_count=to_int_or_none(first_value(row, "kor", "korean", "koreanCount")),
            foreign_count=to_int_or_none(first_value(row, "foreigner", "foreign", "foreignCount")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse IIAC arrival congestion record: {exc}") from exc


def _build_passenger_forecast(row: Mapping[str, Any]) -> PassengerForecast:
    try:
        return PassengerForecast(
            display_date=str(first_value(row, "adate", "displayDate") or ""),
            time_range=str(first_value(row, "atime", "timeRange") or ""),
            t1_arrival_east=to_int_or_none(first_value(row, "t1eg1")),
            t1_arrival_west=to_int_or_none(first_value(row, "t1eg2")),
            t1_departure_total=to_int_or_none(first_value(row, "t1dgsum1")),
            t2_arrival_total=to_int_or_none(first_value(row, "t2egsum1")),
            t2_departure_total=to_int_or_none(first_value(row, "t2dgsum1")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse IIAC passenger forecast record: {exc}") from exc
