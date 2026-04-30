"""한국공항공사(KAC) provider adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pykrairport._convert import first_value, strip_or_none, to_bool_or_none, to_int_or_none
from pykrairport._http import HttpClient, SessionLike
from pykrairport._routing import ensure_kac_airport
from pykrairport._time import parse_kst_datetime
from pykrairport._xml import extract_items
from pykrairport.exceptions import KrairportParseError
from pykrairport.models import AircraftAssignment, Flight, ParkingFee

STATUS_BASE = "https://openapi.airport.co.kr/service/rest/StatusOfFlights"
AIRCRAFT_BASE = "https://openapi.airport.co.kr/service/rest/FlightStatusAPLList"
PARKING_FEE_BASE = "https://openapi.airport.co.kr/service/rest/AirportParkingFee"


class KacClient:
    """Low-level client for Korea Airports Corporation APIs."""

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
        airport_code: str,
        searchday: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        flight_id: str | None = None,
        flight_unique_id: str | None = None,
        line: str | None = None,
        arr_airport_code: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> list[Flight]:
        code = ensure_kac_airport(airport_code)
        params = {
            "searchday": searchday,
            "from_time": from_time,
            "to_time": to_time,
            "airport_code": code,
            "f_id": flight_unique_id,
            "flight_id": flight_id,
            "line": line,
            "arr_airport_code": arr_airport_code,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_xml(f"{STATUS_BASE}/getDepFlightStatusList", params)
        return [
            _build_flight(row, airport_code=code, direction="departure")
            for row in extract_items(data)
        ]

    def arrivals(
        self,
        *,
        airport_code: str,
        searchday: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        flight_id: str | None = None,
        flight_unique_id: str | None = None,
        line: str | None = None,
        dep_airport_code: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> list[Flight]:
        code = ensure_kac_airport(airport_code)
        params = {
            "searchday": searchday,
            "from_time": from_time,
            "to_time": to_time,
            "airport_code": code,
            "f_id": flight_unique_id,
            "flight_id": flight_id,
            "line": line,
            "dep_airport_code": dep_airport_code,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_xml(f"{STATUS_BASE}/getArrFlightStatusList", params)
        return [
            _build_flight(row, airport_code=code, direction="arrival")
            for row in extract_items(data)
        ]

    def aircraft_assignments(
        self,
        *,
        airport_code: str | None = None,
        sch_st_time: str | None = None,
        sch_ed_time: str | None = None,
        flight_id: str | None = None,
        flight_unique_id: str | None = None,
        aircraft_registration: str | None = None,
        aircraft_type: str | None = None,
        line: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> list[AircraftAssignment]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        params = {
            "schStTime": sch_st_time,
            "schEdTime": sch_ed_time,
            "schAirCode": code,
            "schFID": flight_unique_id,
            "schFln": flight_id,
            "Line": line,
            "schAPLno": aircraft_registration,
            "schAPM": aircraft_type,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_xml(f"{AIRCRAFT_BASE}/getFlightStatusAPLList", params)
        return [
            _build_aircraft_assignment(row, requested_airport_code=code)
            for row in extract_items(data)
        ]

    def parking_fees(self, *, airport_code: str | None = None) -> list[ParkingFee]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        params = {"schAirportCode": code}
        data = self._http.get_xml(f"{PARKING_FEE_BASE}/parkingfee", params)
        return [_build_parking_fee(row, requested_airport_code=code) for row in extract_items(data)]


def _build_flight(row: Mapping[str, Any], *, airport_code: str, direction: str) -> Flight:
    try:
        flight_id = str(first_value(row, "flightId", "flight_id", "airFln", "schFln") or "")
        scheduled = parse_kst_datetime(
            first_value(
                row,
                "scheduleDateTime",
                "scheduledatetime",
                "scheduleDatetime",
                "scheduletime",
            )
        )
        estimated = parse_kst_datetime(
            first_value(
                row,
                "estimatedDateTime",
                "estimateddatetime",
                "estimatedDatetime",
                "estimatedtime",
            )
        )
        return Flight(
            provider="kac",
            airport_code=airport_code,
            flight_id=flight_id,
            flight_unique_id=strip_or_none(first_value(row, "f_id", "fid", "schFID")),
            direction="departure" if direction == "departure" else "arrival",
            airline_name=strip_or_none(
                first_value(row, "airline", "airlineKorean", "airlineEnglish")
            ),
            airline_code=strip_or_none(
                first_value(row, "airlineCode", "airlinecode", "schAirCode")
            ),
            departure_airport_code=strip_or_none(
                first_value(row, "depAirportCode", "dep_airport_code")
            ),
            arrival_airport_code=strip_or_none(
                first_value(row, "arrAirportCode", "arr_airport_code")
            ),
            scheduled_at=scheduled,
            estimated_at=estimated,
            status_korean=strip_or_none(first_value(row, "rmkKor", "remarkKor", "statusKor")),
            status_english=strip_or_none(first_value(row, "rmkEng", "remarkEng", "statusEng")),
            terminal=strip_or_none(first_value(row, "terminal", "terminalId", "terminalid")),
            gate=strip_or_none(first_value(row, "gate", "gatenumber", "gateNumber")),
            codeshare=to_bool_or_none(first_value(row, "codeshare", "cdsrYn")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse KAC flight record: {exc}") from exc


def _build_aircraft_assignment(
    row: Mapping[str, Any], *, requested_airport_code: str | None
) -> AircraftAssignment:
    try:
        airport_code = strip_or_none(first_value(row, "airport", "airportCode", "schAirCode"))
        return AircraftAssignment(
            airport_code=airport_code or requested_airport_code or "",
            flight_id=str(first_value(row, "airFln", "flightId", "flight_id", "schFln") or ""),
            flight_unique_id=strip_or_none(first_value(row, "f_id", "fid", "schFID")),
            aircraft_registration=strip_or_none(
                first_value(row, "aplRegNo", "aircraftRegistration", "schAPLno")
            ),
            aircraft_type=strip_or_none(first_value(row, "aircraftType", "aircrafttype", "schAPM")),
            airline_name=strip_or_none(
                first_value(row, "airlineKorean", "airlineEnglish", "airline")
            ),
            scheduled_at=parse_kst_datetime(
                first_value(row, "scheduleDateTime", "scheduledatetime", "scheduletime")
            ),
            estimated_at=parse_kst_datetime(
                first_value(row, "estimatedDateTime", "estimateddatetime", "estimatedtime")
            ),
            gate=strip_or_none(
                first_value(row, "boardingKor", "boardingEng", "gate", "gatenumber")
            ),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse KAC aircraft record: {exc}") from exc


def _build_parking_fee(row: Mapping[str, Any], *, requested_airport_code: str | None) -> ParkingFee:
    try:
        airport_code = strip_or_none(first_value(row, "airportCode", "schAirportCode"))
        return ParkingFee(
            airport_code=airport_code or requested_airport_code or "",
            parking_name=strip_or_none(
                first_value(row, "parkingName", "parkingArea", "parkingDiv")
            ),
            small_basic_minutes=to_int_or_none(first_value(row, "parkingBasicM")),
            small_basic_fee=to_int_or_none(first_value(row, "parkingBasicAccount")),
            large_basic_minutes=to_int_or_none(first_value(row, "parkingBasicMd")),
            large_basic_fee=to_int_or_none(first_value(row, "parkingBasicAccountd")),
            small_daily_max_fee=to_int_or_none(
                first_value(row, "parkingDayMaxAccount", "parkingOneDayAccount")
            ),
            large_daily_max_fee=to_int_or_none(
                first_value(row, "parkingDayMaxAccountd", "parkingOneDayAccountd")
            ),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse KAC parking fee record: {exc}") from exc
