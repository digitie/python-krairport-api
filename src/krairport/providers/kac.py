"""한국공항공사(KAC) 공급자 어댑터."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from krairport._convert import first_value, strip_or_none, to_bool_or_none, to_int_or_none
from krairport._http import AsyncHttpClient, AsyncSessionLike, HttpClient, SessionLike
from krairport._routing import ensure_kac_airport
from krairport._time import parse_kst_datetime
from krairport._xml import extract_items
from krairport.enums import Direction, Provider, normalize_direction
from krairport.exceptions import KrairportParseError
from krairport.geo import Coordinate, address_from_mapping
from krairport.models import (
    AircraftAssignment,
    AirportFacility,
    BusRoute,
    Flight,
    FlightSchedule,
    ParkingAreaStatus,
    ParkingFee,
    TaxiStatus,
)

STATUS_BASE = "https://openapi.airport.co.kr/service/rest/StatusOfFlights"
AIRCRAFT_BASE = "https://openapi.airport.co.kr/service/rest/FlightStatusAPLList"
PARKING_FEE_BASE = "https://openapi.airport.co.kr/service/rest/AirportParkingFee"
FLIGHT_SCHEDULE_BASE = "https://openapi.airport.co.kr/service/rest/FlightScheduleList"
PARKING_CONGESTION_BASE = (
    "https://openapi.airport.co.kr/service/rest/AirportParkingCongestion"
)
AIRPORT_PARKING_BASE = "https://openapi.airport.co.kr/service/rest/AirportParking"
AIRPORT_FACILITIES_BASE = "https://openapi.airport.co.kr/service/rest/AirportFacilities"
AIRPORT_BUS_BASE = "https://openapi.airport.co.kr/service/rest/AirportBusInfo"
JEJU_TAXI_WAIT_BASE = "https://openapi.airport.co.kr/service/rest/taxiWaitInfo"
_SAFE_PATH_PART = re.compile(r"^[A-Za-z0-9_]+$")


class KacClient:
    """한국공항공사 API용 저수준 클라이언트."""

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

    def __enter__(self) -> KacClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

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
            _build_flight(row, airport_code=code, direction=Direction.DEPARTURE)
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
            _build_flight(row, airport_code=code, direction=Direction.ARRIVAL)
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

    def flight_schedules(
        self,
        *,
        direction: str | Direction,
        airport_code: str | None = None,
        counterpart_airport_code: str | None = None,
        sch_date: str | None = None,
        airline_code: str | None = None,
        flight_id: str | None = None,
        international: bool = False,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[FlightSchedule]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        operation = "getIflightScheduleList" if international else "getDflightScheduleList"
        direction_value = normalize_direction(direction)
        if direction_value is Direction.DEPARTURE:
            dept_code = code
            arrv_code = counterpart_airport_code
        elif direction_value is Direction.ARRIVAL:
            dept_code = counterpart_airport_code
            arrv_code = code
        params = {
            "schDate": sch_date,
            "schDeptCityCode": dept_code,
            "schArrvCityCode": arrv_code,
            "schAirLine": airline_code,
            "schFlightNum": flight_id,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_xml(f"{FLIGHT_SCHEDULE_BASE}/{operation}", params)
        return [
            _build_flight_schedule(row, direction=direction_value, international=international)
            for row in extract_items(data)
        ]

    def parking_status(
        self,
        *,
        airport_code: str,
        page_no: int = 1,
        num_of_rows: int = 100,
        realtime: bool = False,
    ) -> list[ParkingAreaStatus]:
        code = ensure_kac_airport(airport_code)
        params: dict[str, Any]
        if realtime:
            url = f"{AIRPORT_PARKING_BASE}/airportparkingRT"
            params = {"schAirportCode": code}
        else:
            url = f"{PARKING_CONGESTION_BASE}/airportParkingCongestionRT"
            params = {"schAirportCode": code, "pageNo": page_no, "numOfRows": num_of_rows}
        data = self._http.get_xml(url, params)
        return [
            _build_parking_status(row, requested_airport_code=code)
            for row in extract_items(data)
        ]

    def airport_facilities(
        self,
        *,
        airport_code: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[AirportFacility]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        params = {"apcd": code, "pageNo": page_no, "numOfRows": num_of_rows}
        data = self._http.get_xml(f"{AIRPORT_FACILITIES_BASE}/getAirportFacilities", params)
        return [
            _build_airport_facility(row, requested_airport_code=code)
            for row in extract_items(data)
        ]

    def airport_buses(
        self,
        *,
        airport_code: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[BusRoute]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        params = {"schAirport": code, "pageNo": page_no, "numOfRows": num_of_rows}
        data = self._http.get_xml(f"{AIRPORT_BUS_BASE}/businfo", params)
        return [
            _build_bus_route(row, provider=Provider.KAC, airport_code=code)
            for row in extract_items(data)
        ]

    def jeju_taxi_wait(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[TaxiStatus]:
        params = {"pageNo": page_no, "numOfRows": num_of_rows}
        data = self._http.get_xml(f"{JEJU_TAXI_WAIT_BASE}/getJejuTaxiWaitInfo", params)
        return [
            _build_taxi_status(row, provider=Provider.KAC, airport_code="CJU")
            for row in extract_items(data)
        ]

    def raw_items(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """KAC REST 서비스 작업의 정규화된 XML item 목록을 반환합니다."""

        _validate_path_part(service)
        _validate_path_part(operation)
        data = self._http.get_xml(
            f"https://openapi.airport.co.kr/service/rest/{service}/{operation}",
            dict(params or {}),
        )
        return extract_items(data)


class AsyncKacClient:
    """Async KAC API adapter backed by httpx.AsyncClient."""

    def __init__(
        self,
        service_key: str | None,
        *,
        session: AsyncSessionLike | None = None,
        timeout: float = 10.0,
        retries: int = 3,
    ) -> None:
        self._http = AsyncHttpClient(
            service_key,
            session=session,
            timeout=timeout,
            retries=retries,
        )

    async def __aenter__(self) -> AsyncKacClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def departures(
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
        data = await self._http.get_xml(f"{STATUS_BASE}/getDepFlightStatusList", params)
        return [
            _build_flight(row, airport_code=code, direction=Direction.DEPARTURE)
            for row in extract_items(data)
        ]

    async def arrivals(
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
        data = await self._http.get_xml(f"{STATUS_BASE}/getArrFlightStatusList", params)
        return [
            _build_flight(row, airport_code=code, direction=Direction.ARRIVAL)
            for row in extract_items(data)
        ]

    async def aircraft_assignments(
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
        data = await self._http.get_xml(f"{AIRCRAFT_BASE}/getFlightStatusAPLList", params)
        return [
            _build_aircraft_assignment(row, requested_airport_code=code)
            for row in extract_items(data)
        ]

    async def parking_fees(self, *, airport_code: str | None = None) -> list[ParkingFee]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        params = {"schAirportCode": code}
        data = await self._http.get_xml(f"{PARKING_FEE_BASE}/parkingfee", params)
        return [_build_parking_fee(row, requested_airport_code=code) for row in extract_items(data)]

    async def flight_schedules(
        self,
        *,
        direction: str | Direction,
        airport_code: str | None = None,
        counterpart_airport_code: str | None = None,
        sch_date: str | None = None,
        airline_code: str | None = None,
        flight_id: str | None = None,
        international: bool = False,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[FlightSchedule]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        operation = "getIflightScheduleList" if international else "getDflightScheduleList"
        direction_value = normalize_direction(direction)
        if direction_value is Direction.DEPARTURE:
            dept_code = code
            arrv_code = counterpart_airport_code
        elif direction_value is Direction.ARRIVAL:
            dept_code = counterpart_airport_code
            arrv_code = code
        params = {
            "schDate": sch_date,
            "schDeptCityCode": dept_code,
            "schArrvCityCode": arrv_code,
            "schAirLine": airline_code,
            "schFlightNum": flight_id,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = await self._http.get_xml(f"{FLIGHT_SCHEDULE_BASE}/{operation}", params)
        return [
            _build_flight_schedule(row, direction=direction_value, international=international)
            for row in extract_items(data)
        ]

    async def parking_status(
        self,
        *,
        airport_code: str,
        page_no: int = 1,
        num_of_rows: int = 100,
        realtime: bool = False,
    ) -> list[ParkingAreaStatus]:
        code = ensure_kac_airport(airport_code)
        params: dict[str, Any]
        if realtime:
            url = f"{AIRPORT_PARKING_BASE}/airportparkingRT"
            params = {"schAirportCode": code}
        else:
            url = f"{PARKING_CONGESTION_BASE}/airportParkingCongestionRT"
            params = {"schAirportCode": code, "pageNo": page_no, "numOfRows": num_of_rows}
        data = await self._http.get_xml(url, params)
        return [
            _build_parking_status(row, requested_airport_code=code)
            for row in extract_items(data)
        ]

    async def airport_facilities(
        self,
        *,
        airport_code: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[AirportFacility]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        params = {"apcd": code, "pageNo": page_no, "numOfRows": num_of_rows}
        data = await self._http.get_xml(f"{AIRPORT_FACILITIES_BASE}/getAirportFacilities", params)
        return [
            _build_airport_facility(row, requested_airport_code=code)
            for row in extract_items(data)
        ]

    async def airport_buses(
        self,
        *,
        airport_code: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[BusRoute]:
        code = ensure_kac_airport(airport_code) if airport_code else None
        params = {"schAirport": code, "pageNo": page_no, "numOfRows": num_of_rows}
        data = await self._http.get_xml(f"{AIRPORT_BUS_BASE}/businfo", params)
        return [
            _build_bus_route(row, provider=Provider.KAC, airport_code=code)
            for row in extract_items(data)
        ]

    async def jeju_taxi_wait(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[TaxiStatus]:
        params = {"pageNo": page_no, "numOfRows": num_of_rows}
        data = await self._http.get_xml(f"{JEJU_TAXI_WAIT_BASE}/getJejuTaxiWaitInfo", params)
        return [
            _build_taxi_status(row, provider=Provider.KAC, airport_code="CJU")
            for row in extract_items(data)
        ]

    async def raw_items(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return normalized raw XML items from a KAC REST service operation."""

        _validate_path_part(service)
        _validate_path_part(operation)
        data = await self._http.get_xml(
            f"https://openapi.airport.co.kr/service/rest/{service}/{operation}",
            dict(params or {}),
        )
        return extract_items(data)


def _build_flight(row: Mapping[str, Any], *, airport_code: str, direction: Direction) -> Flight:
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
            provider=Provider.KAC,
            airport_code=airport_code,
            flight_id=flight_id,
            flight_unique_id=strip_or_none(first_value(row, "f_id", "fid", "schFID")),
            direction=direction,
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


def _build_flight_schedule(
    row: Mapping[str, Any], *, direction: Direction, international: bool
) -> FlightSchedule:
    return FlightSchedule(
        provider=Provider.KAC,
        direction=direction,
        flight_id=str(first_value(row, "domesticNum", "internationalNum", "flightNum") or ""),
        airline_code=strip_or_none(first_value(row, "airlineKorean", "airlineEnglish", "airline")),
        airline_name=strip_or_none(first_value(row, "airlineKorean", "airlineEnglish")),
        departure_airport_code=strip_or_none(
            first_value(row, "startcity", "schDeptCityCode", "deptCityCode")
        ),
        arrival_airport_code=strip_or_none(
            first_value(row, "arrivalcity", "schArrvCityCode", "arrvCityCode")
        ),
        scheduled_time=strip_or_none(first_value(row, "domesticStartTime", "internationalTime")),
        start_date=strip_or_none(first_value(row, "domesticStdate", "internationalStdate")),
        end_date=strip_or_none(first_value(row, "domesticEddate", "internationalEddate")),
        days=strip_or_none(first_value(row, "domesticMon", "internationalMon", "days")),
        season="international" if international else "domestic",
        raw=dict(row),
    )


def _build_parking_status(
    row: Mapping[str, Any], *, requested_airport_code: str
) -> ParkingAreaStatus:
    try:
        return ParkingAreaStatus(
            airport_code=str(
                first_value(row, "airportCode", "parkingAirportCode", "schAirportCode")
                or requested_airport_code
            ),
            terminal=strip_or_none(first_value(row, "terminal", "terminalId")),
            parking_area=str(
                first_value(row, "parkingName", "parkingArea", "parkingAirportName") or ""
            ),
            occupied=to_int_or_none(
                first_value(row, "parkingOccupiedSpace", "occupied", "parkingIstay")
            ),
            capacity=to_int_or_none(
                first_value(row, "parkingTotalSpace", "capacity", "parkingFullSpace")
            ),
            updated_at=parse_kst_datetime(first_value(row, "sysGetdate", "datetm", "updateTime")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse KAC parking status record: {exc}") from exc


def _build_airport_facility(
    row: Mapping[str, Any], *, requested_airport_code: str | None
) -> AirportFacility:
    return AirportFacility(
        provider=Provider.KAC,
        airport_code=strip_or_none(first_value(row, "apcd", "airportCode"))
        or requested_airport_code,
        terminal=strip_or_none(first_value(row, "terminal", "terminalId")),
        name=str(first_value(row, "facilityNm", "facilityName", "name") or ""),
        category=strip_or_none(first_value(row, "lclas", "category", "facilityType")),
        floor=strip_or_none(first_value(row, "floor", "floorInfo")),
        location=strip_or_none(first_value(row, "loc", "location", "area")),
        address=address_from_mapping(row),
        business_hours=strip_or_none(first_value(row, "operTime", "businessHours")),
        telephone=strip_or_none(first_value(row, "tel", "telephone", "phone")),
        coordinate=Coordinate.from_mapping(row),
        raw=dict(row),
    )


def _build_bus_route(
    row: Mapping[str, Any], *, provider: Provider, airport_code: str | None
) -> BusRoute:
    try:
        return BusRoute(
            provider=provider,
            airport_code=strip_or_none(first_value(row, "airportCode", "schAirport"))
            or airport_code,
            area=strip_or_none(first_value(row, "area", "region")),
            bus_number=str(first_value(row, "busnumber", "busNo", "busNum") or ""),
            bus_class=strip_or_none(first_value(row, "busclass", "busClass", "busType")),
            operator=strip_or_none(first_value(row, "company", "operator", "busCompany")),
            platform=strip_or_none(first_value(row, "t1wdayt", "platform", "rideLocation")),
            adult_fare=to_int_or_none(first_value(row, "adultfare", "adultFare", "fare")),
            route_info=strip_or_none(first_value(row, "routeinfo", "routeInfo", "route")),
            first_time_to_airport=strip_or_none(first_value(row, "toawfirst", "firstTime")),
            last_time_to_airport=strip_or_none(first_value(row, "toawlast", "lastTime")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse KAC bus route record: {exc}") from exc


def _build_taxi_status(
    row: Mapping[str, Any], *, provider: Provider, airport_code: str | None
) -> TaxiStatus:
    try:
        return TaxiStatus(
            provider=provider,
            airport_code=airport_code,
            terminal=strip_or_none(first_value(row, "terno", "terminal", "terminalId")),
            stand=strip_or_none(first_value(row, "stand", "taxistand", "bestVantaxistand")),
            seoul_count=to_int_or_none(first_value(row, "seoultaxicnt", "seoulCount")),
            incheon_count=to_int_or_none(first_value(row, "incheontaxicnt", "incheonCount")),
            gyeonggi_count=to_int_or_none(first_value(row, "gyenggitaxicnt", "gyeonggiCount")),
            intercity_count=to_int_or_none(first_value(row, "intercitytaxicnt", "intercityCount")),
            deluxe_count=to_int_or_none(first_value(row, "besttaxicnt", "deluxeCount")),
            jumbo_count=to_int_or_none(first_value(row, "jumbotaxicnt", "jumboCount")),
            updated_at=parse_kst_datetime(first_value(row, "datetm", "updatedAt", "sysGetdate")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse taxi status record: {exc}") from exc


def _validate_path_part(value: str) -> None:
    if not _SAFE_PATH_PART.fullmatch(value):
        raise ValueError(f"unsafe KAC service path component: {value!r}")
