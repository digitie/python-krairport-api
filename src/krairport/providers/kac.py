"""한국공항공사(KAC) 공급자 어댑터."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

from krairport._convert import first_value, strip_or_none, to_bool_or_none, to_int_or_none
from krairport._http import HttpClient, SessionLike
from krairport._ratelimit import AsyncTokenBucket
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

STATUS_BASE = "https://apis.data.go.kr/B551178/flight-status"
AIRCRAFT_BASE = "http://openapi.airport.co.kr/service/rest/FlightStatusAPLList"
PARKING_FEE_BASE = "http://openapi.airport.co.kr/service/rest/AirportParkingFee"
FLIGHT_SCHEDULE_BASE = "http://openapi.airport.co.kr/service/rest/FlightScheduleList"
PARKING_CONGESTION_BASE = (
    "http://openapi.airport.co.kr/service/rest/AirportParkingCongestion"
)
AIRPORT_PARKING_BASE = "http://openapi.airport.co.kr/service/rest/AirportParking"
AIRPORT_FACILITIES_BASE = "http://openapi.airport.co.kr/service/rest/AirportFacilities"
AIRPORT_BUS_BASE = "http://openapi.airport.co.kr/service/rest/AirportBusInfo"
JEJU_TAXI_WAIT_BASE = "http://openapi.airport.co.kr/service/rest/taxiWaitInfo"
FLIGHT_STATUS_DETAIL_URL = "https://api.odcloud.kr/api/FlightStatusListDTL/v1/getFlightStatusListDetail"
_SAFE_PATH_PART = re.compile(r"^[A-Za-z0-9_]+$")




class KacClient:
    """한국공항공사 비동기 API 클라이언트."""

    def __init__(
        self,
        service_key: str | None,
        *,
        session: SessionLike | None = None,
        timeout: float = 10.0,
        retries: int = 3,
        max_rps: float = 5.0,
        rate_limiter: AsyncTokenBucket | None = None,
    ) -> None:
        self._http = HttpClient(
            service_key,
            session=session,
            timeout=timeout,
            retries=retries,
            max_rps=max_rps,
            rate_limiter=rate_limiter,
        )

    async def __aenter__(self) -> KacClient:
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
        data = await self._http.get_xml(f"{STATUS_BASE}/depart", params)
        return [
            _build_flight(row, airport_code=code, direction=Direction.DEPARTURE)
            for row in _flight_list_rows(data, page_no)
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
        data = await self._http.get_xml(f"{STATUS_BASE}/arrival", params)
        return [
            _build_flight(row, airport_code=code, direction=Direction.ARRIVAL)
            for row in _flight_list_rows(data, page_no)
        ]

    async def flight_status(
        self,
        *,
        airport_code: str,
        searchday: str,
        num_of_rows: int = 100,
        max_pages: int = 20,
    ) -> list[Flight]:
        """조회일의 제공 범위를 페이지 메타데이터로 끝까지 읽고, 불완전하면 실패한다.

        max_pages는 출발·도착을 합한 논리 페이지 상한이다. HTTP 재시도는 별도다.
        서버의 페이지 크기 축소를
        수용하지만 중간 빈 페이지, 반복·변경된 범위, 예산 소진을 성공으로 숨기지 않는다.
        """
        code = ensure_kac_airport(airport_code)
        if not re.fullmatch(r"[0-9]{8}", searchday):
            raise ValueError("searchday는 YYYYMMDD 형식이어야 합니다.")
        datetime.strptime(searchday, "%Y%m%d")
        if type(num_of_rows) is not int or not 1 <= num_of_rows <= 1000:
            raise ValueError("num_of_rows는 1~1000 정수여야 합니다.")
        if type(max_pages) is not int or not 2 <= max_pages <= 100:
            raise ValueError("max_pages는 2~100 정수여야 합니다.")
        flights: list[Flight] = []
        calls = 0
        for direction, operation in [
            (Direction.DEPARTURE, "depart"), (Direction.ARRIVAL, "arrival")
        ]:
            page_no = 1
            expected_total: int | None = None
            expected_size: int | None = None
            identities: set[tuple[str, str, str]] = set()
            while True:
                if calls >= max_pages:
                    raise KrairportParseError("KAC 출도착 페이지 예산 소진: 불완전한 결과")
                data = await self._http.get_xml(f"{STATUS_BASE}/{operation}", {
                    "airport_code": code, "searchday": searchday,
                    "pageNo": page_no, "numOfRows": num_of_rows,
                })
                calls += 1
                rows, total, size = _flight_page_rows(data, page_no)
                if expected_total is not None and (
                    total != expected_total or size != expected_size
                ):
                    raise KrairportParseError("KAC 출도착 페이지 범위가 조회 중 변경되었습니다.")
                expected_total, expected_size = total, size
                for row in rows:
                    flight = _build_flight(row, airport_code=code, direction=direction)
                    if not flight.flight_id or flight.scheduled_at is None:
                        raise KrairportParseError("KAC 출도착 편명/예정시각이 없습니다.")
                    identity = (("fid", flight.flight_unique_id, "") if flight.flight_unique_id
                        else ("schedule", flight.flight_id, flight.scheduled_at.isoformat()))
                    if identity in identities:
                        raise KrairportParseError("KAC 출도착 페이지에 중복 항공편이 있습니다.")
                    identities.add(identity)
                    flights.append(flight)
                if page_no * size >= total:
                    break
                page_no += 1
        return flights

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
        """한국공항공사 REST 서비스의 XML 원시 항목을 정규화해 반환한다."""

        _validate_path_part(service)
        _validate_path_part(operation)
        data = await self._http.get_xml(
            f"http://openapi.airport.co.kr/service/rest/{service}/{operation}",
            dict(params or {}),
        )
        return extract_items(data)

    async def flight_status_detail_raw_items(
        self,
        *,
        airport_code: str,
        flight_date: str,
        page: int = 1,
        per_page: int = 1000,
    ) -> list[dict[str, Any]]:
        """한국공항공사 ODCloud 상세 운항정보의 원시 항목을 반환한다.

        FlightStatusListDTL은 api.odcloud.kr에서 {"data": [...]} 형태의
        JSON을 반환하므로 XML을 처리하는 raw_items()와 별도로 요청한다.
        """

        code = ensure_kac_airport(airport_code)
        params = {
            "page": page,
            "perPage": per_page,
            "returnType": "JSON",
            "cond[FLIGHT_DATE::EQ]": flight_date,
            "cond[AIRPORT::EQ]": code,
        }
        data = await self._http.get_json(FLIGHT_STATUS_DETAIL_URL, params)
        items = data.get("data", [])
        return [item for item in items if isinstance(item, dict)]


def _flight_response_body(data: Mapping[str, Any]) -> Mapping[str, Any]:
    response = data.get("response")
    if not isinstance(response, Mapping) or not isinstance(response.get("body"), Mapping):
        raise KrairportParseError("KAC 출도착 페이지 body가 없습니다.")
    header = response.get("header")
    if not isinstance(header, Mapping) or str(header.get("resultCode")) not in {"00", "0"}:
        raise KrairportParseError("KAC 출도착 성공 상태가 없습니다.")
    return cast(Mapping[str, Any], response["body"])


def _flight_list_rows(data: Mapping[str, Any], page_no: int) -> list[dict[str, Any]]:
    body = _flight_response_body(data)
    if any(field in body for field in ("pageNo", "numOfRows", "totalCount")):
        return _flight_page_rows(data, page_no)[0]
    # 과거 단일 페이지 응답은 메타데이터가 없지만 항목의 손상은 허용하지 않는다.
    items = body.get("items")
    if items in (None, ""):
        return []
    if not isinstance(items, Mapping) or (items and "item" not in items):
        raise KrairportParseError("KAC 출도착 항목 구조가 올바르지 않습니다.")
    return extract_items(data)


def _flight_page_rows(
    data: Mapping[str, Any], page_no: int,
) -> tuple[list[dict[str, Any]], int, int]:
    body = _flight_response_body(data)
    numbers = []
    for field in ("pageNo", "numOfRows", "totalCount"):
        value = body.get(field)
        if isinstance(value, bool) or not re.fullmatch(r"[0-9]{1,10}", str(value)):
            raise KrairportParseError("KAC 출도착 페이지 메타데이터가 올바르지 않습니다.")
        numbers.append(int(str(value)))
    page, size, total = numbers
    if page != page_no or size < 1 or (total == 0 and page != 1):
        raise KrairportParseError("KAC 출도착 페이지 범위가 올바르지 않습니다.")
    items = body.get("items")
    if total > 0 and not isinstance(items, Mapping):
        raise KrairportParseError("KAC 출도착 페이지 항목이 없습니다.")
    if not isinstance(items, Mapping) and items not in (None, ""):
        raise KrairportParseError("KAC 출도착 페이지 항목 구조가 올바르지 않습니다.")
    rows = extract_items(data)
    if len(rows) != max(0, min(size, total - (page - 1) * size)):
        raise KrairportParseError("KAC 출도착 페이지 항목 수가 맞지 않습니다.")
    return rows, total, size


def _build_flight(row: Mapping[str, Any], *, airport_code: str, direction: Direction) -> Flight:
    try:
        flight_id = str(
            first_value(row, "flightId", "flightid", "flight_id", "airFln", "schFln") or ""
        )
        scheduled = parse_kst_datetime(
            first_value(
                row,
                "scheduleDateTime",
                "scheduledatetime",
                "scheduleDatetime",
                "scheduletime",
            ), require_time=True,
        )
        estimated = parse_kst_datetime(
            first_value(
                row,
                "estimatedDateTime",
                "estimateddatetime",
                "estimatedDatetime",
                "estimatedtime",
            ), require_time=True,
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
                first_value(row, "arrAirportCode", "arrvAirportCode", "arr_airport_code")
            ),
            departure_airport_name=strip_or_none(first_value(row, "depAirport")),
            arrival_airport_name=strip_or_none(first_value(row, "arrAirport", "arrvAirport")),
            line_type=strip_or_none(first_value(row, "line")),
            scheduled_at=scheduled,
            estimated_at=estimated,
            status_korean=strip_or_none(first_value(row, "rmkKor", "remarkKor", "statusKor")),
            status_english=strip_or_none(first_value(row, "rmkEng", "remarkEng", "statusEng")),
            terminal=strip_or_none(first_value(row, "terminal", "terminalId", "terminalid")),
            gate=strip_or_none(first_value(row, "gate", "gatenumber", "gateNumber")),
            codeshare=to_bool_or_none(first_value(row, "codeshare", "cdsrYn")),
            master_flight_id=strip_or_none(first_value(row, "masterflightid")),
            raw=dict(row),
        )
    except (TypeError, ValueError):
        raise KrairportParseError("KAC 항공편 응답을 해석할 수 없습니다.") from None


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
