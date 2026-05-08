"""인천국제공항공사(IIAC) 공급자 어댑터."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pykrairport._convert import (
    as_list,
    first_value,
    strip_or_none,
    to_bool_or_none,
    to_float_or_none,
    to_int_or_none,
)
from pykrairport._http import HttpClient, SessionLike
from pykrairport._routing import ensure_iiac_airport
from pykrairport._time import parse_kst_datetime
from pykrairport.enums import Direction, Provider, normalize_direction
from pykrairport.exceptions import KrairportParseError
from pykrairport.geo import coordinate_from_mapping
from pykrairport.models import (
    AirportFacility,
    ArrivalCongestion,
    BusRoute,
    Flight,
    FlightSchedule,
    ParkingAreaStatus,
    PassengerForecast,
    ServiceDestination,
    TaxiStatus,
    WorldWeather,
)

DETAILED_FLIGHTS_BASE = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsDeOdp"
TODAY_FLIGHTS_BASE = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp"
PARKING_BASE = "http://apis.data.go.kr/B551177/StatusOfParking"
ARRIVAL_CONGESTION_BASE = "http://apis.data.go.kr/B551177/StatusOfArrivals"
PASSENGER_FORECAST_BASE = "http://apis.data.go.kr/B551177/PassengerNoticeKR"
TAXI_BASE = "http://apis.data.go.kr/B551177/StatusOfTaxi"
BUS_BASE = "http://apis.data.go.kr/B551177/BusInformation"
WEATHER_BASE = "http://apis.data.go.kr/B551177/StatusOfPassengerWorldWeatherInfo"
PAX_SCHEDULE_BASE = "http://apis.data.go.kr/B551177/PaxFltSched"
DESTINATION_BASE = "http://apis.data.go.kr/B551177/StatusOfSrvDestinations"
FACILITY_BASE = "http://apis.data.go.kr/B551177/StatusOfFacility"
_SAFE_PATH_PART = re.compile(r"^[A-Za-z0-9_]+$")


class IiacClient:
    """인천국제공항공사 API용 저수준 클라이언트."""

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
        return [_build_flight(row, direction=Direction.DEPARTURE) for row in _extract_items(data)]

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
        return [_build_flight(row, direction=Direction.ARRIVAL) for row in _extract_items(data)]

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

    def taxi_status(
        self,
        *,
        airport_code: str = "ICN",
        terminal: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[TaxiStatus]:
        ensure_iiac_airport(airport_code)
        params = {
            "type": "json",
            "terno": terminal,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{TAXI_BASE}/getTaxiStatus", params)
        return [_build_taxi_status(row, terminal_hint=terminal) for row in _extract_items(data)]

    def bus_routes(
        self,
        *,
        airport_code: str = "ICN",
        area: str = "1",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[BusRoute]:
        ensure_iiac_airport(airport_code)
        params = {"type": "json", "area": area, "pageNo": page_no, "numOfRows": num_of_rows}
        data = self._http.get_json(f"{BUS_BASE}/getBusInfo", params)
        return [_build_bus_route(row) for row in _extract_items(data)]

    def world_weather(
        self,
        *,
        direction: str | Direction,
        airport_code: str = "ICN",
        from_time: str | None = None,
        to_time: str | None = None,
        airport: str | None = None,
        flight_id: str | None = None,
        airline_code: str | None = None,
        lang: str = "K",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[WorldWeather]:
        ensure_iiac_airport(airport_code)
        direction_value = normalize_direction(direction)
        if direction_value is Direction.ARRIVAL:
            operation = "getPassengerArrivalsWorldWeather"
        elif direction_value is Direction.DEPARTURE:
            operation = "getPassengerDeparturesWorldWeather"
        params = {
            "type": "json",
            "from_time": from_time,
            "to_time": to_time,
            "airport": airport,
            "flight_id": flight_id,
            "airline": airline_code,
            "lang": lang,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{WEATHER_BASE}/{operation}", params)
        return [
            _build_world_weather(row, direction=direction_value)
            for row in _extract_items(data)
        ]

    def flight_schedules(
        self,
        *,
        direction: str | Direction,
        airport_code: str = "ICN",
        counterpart_airport_code: str | None = None,
        airline_code: str | None = None,
        flight_id: str | None = None,
        lang: str = "K",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[FlightSchedule]:
        ensure_iiac_airport(airport_code)
        direction_value = normalize_direction(direction)
        if direction_value is Direction.ARRIVAL:
            operation = "getPaxFltSchedArrivals"
        elif direction_value is Direction.DEPARTURE:
            operation = "getPaxFltSchedDepartures"
        params = {
            "type": "json",
            "airport_code": counterpart_airport_code,
            "airline": airline_code,
            "flight_id": flight_id,
            "lang": lang,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{PAX_SCHEDULE_BASE}/{operation}", params)
        return [
            _build_flight_schedule(row, direction=direction_value)
            for row in _extract_items(data)
        ]

    def service_destinations(
        self,
        *,
        airport_code: str | None = None,
        lang: str = "K",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ServiceDestination]:
        params = {
            "type": "json",
            "airport_code": airport_code,
            "lang": lang,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{DESTINATION_BASE}/getServiceDestinationInfo", params)
        return [_build_service_destination(row) for row in _extract_items(data)]

    def facilities(
        self,
        *,
        airport_code: str = "ICN",
        facility_name: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[AirportFacility]:
        ensure_iiac_airport(airport_code)
        params = {
            "type": "json",
            "facility_nm": facility_name,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        data = self._http.get_json(f"{FACILITY_BASE}/getFacilityKR", params)
        return [_build_facility(row) for row in _extract_items(data)]

    def raw_items(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """IIAC B551177 서비스 작업의 정규화된 JSON item 목록을 반환합니다."""

        _validate_path_part(service)
        _validate_path_part(operation)
        request_params = {"type": "json"} | dict(params or {})
        data = self._http.get_json(
            f"http://apis.data.go.kr/B551177/{service}/{operation}",
            request_params,
        )
        return _extract_items(data)


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


def _build_flight(row: Mapping[str, Any], *, direction: Direction) -> Flight:
    try:
        flight_id = str(first_value(row, "flightId", "flight_id", "airFln", "airfln") or "")
        return Flight(
            provider=Provider.IIAC,
            airport_code="ICN",
            flight_id=flight_id,
            flight_unique_id=strip_or_none(first_value(row, "f_id", "fid", "ufid")),
            direction=direction,
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


def _build_taxi_status(row: Mapping[str, Any], *, terminal_hint: str | None) -> TaxiStatus:
    try:
        return TaxiStatus(
            provider=Provider.IIAC,
            airport_code="ICN",
            terminal=strip_or_none(first_value(row, "terno", "terminal")) or terminal_hint,
            stand=strip_or_none(first_value(row, "taxistand", "bestVantaxistand", "stand")),
            seoul_count=to_int_or_none(first_value(row, "seoultaxicnt", "seoulCount")),
            incheon_count=to_int_or_none(first_value(row, "incheontaxicnt", "incheonCount")),
            gyeonggi_count=to_int_or_none(first_value(row, "gyenggitaxicnt", "gyeonggiCount")),
            intercity_count=to_int_or_none(first_value(row, "intercitytaxicnt")),
            deluxe_count=to_int_or_none(first_value(row, "besttaxicnt", "deluxeCount")),
            jumbo_count=to_int_or_none(first_value(row, "jumbotaxicnt", "jumboCount")),
            updated_at=parse_kst_datetime(first_value(row, "datetm", "updatedAt")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse IIAC taxi status record: {exc}") from exc


def _build_bus_route(row: Mapping[str, Any]) -> BusRoute:
    try:
        return BusRoute(
            provider=Provider.IIAC,
            airport_code="ICN",
            area=strip_or_none(first_value(row, "area")),
            bus_number=str(first_value(row, "busnumber", "busNo", "busNum") or ""),
            bus_class=strip_or_none(first_value(row, "busclass", "busClass")),
            operator=strip_or_none(first_value(row, "buscompany", "company", "operator")),
            platform=strip_or_none(first_value(row, "t1wdayt", "platform", "busstop")),
            adult_fare=to_int_or_none(first_value(row, "adultfare", "adultFare", "fare")),
            route_info=strip_or_none(first_value(row, "routeinfo", "routeInfo", "route")),
            first_time_to_airport=strip_or_none(first_value(row, "toawfirst", "firstTime")),
            last_time_to_airport=strip_or_none(first_value(row, "toawlast", "lastTime")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse IIAC bus route record: {exc}") from exc


def _build_world_weather(row: Mapping[str, Any], *, direction: Direction) -> WorldWeather:
    try:
        return WorldWeather(
            direction=direction,
            flight_id=strip_or_none(first_value(row, "flightId", "flight_id", "airFln")),
            airline_name=strip_or_none(first_value(row, "airline", "airlineKorean")),
            airport_code=strip_or_none(first_value(row, "airport", "airportCode")),
            airport_name=strip_or_none(
                first_value(row, "airportNm", "airportName", "airportKorean")
            ),
            scheduled_at=parse_kst_datetime(
                first_value(row, "scheduleDateTime", "scheduledatetime", "scheduletime")
            ),
            estimated_at=parse_kst_datetime(
                first_value(row, "estimatedDateTime", "estimateddatetime", "estimatedtime")
            ),
            terminal=strip_or_none(first_value(row, "terminalid", "terminal")),
            weather=strip_or_none(first_value(row, "weather", "wthr", "weatherStatus")),
            temperature=to_float_or_none(first_value(row, "temperature", "temp", "obsrValue")),
            feels_like=to_float_or_none(first_value(row, "sensorytem", "feelsLike")),
            humidity=to_int_or_none(first_value(row, "humidity", "hum")),
            wind_speed=to_float_or_none(first_value(row, "wind", "windSpeed")),
            raw=dict(row),
        )
    except (TypeError, ValueError) as exc:
        raise KrairportParseError(f"failed to parse IIAC weather record: {exc}") from exc


def _build_flight_schedule(row: Mapping[str, Any], *, direction: Direction) -> FlightSchedule:
    return FlightSchedule(
        provider=Provider.IIAC,
        direction=direction,
        flight_id=str(first_value(row, "flightId", "flight_id", "fltNo") or ""),
        airline_code=strip_or_none(first_value(row, "airlineCode", "airline")),
        airline_name=strip_or_none(first_value(row, "airlineNm", "airlineName", "airlineKorean")),
        departure_airport_code=strip_or_none(
            first_value(row, "departureAirportCode", "depAirportCode", "airport")
        ),
        arrival_airport_code=strip_or_none(
            first_value(row, "arrivalAirportCode", "arrAirportCode", "airport")
        ),
        scheduled_time=strip_or_none(first_value(row, "scheduleTime", "scheduletime", "std")),
        start_date=strip_or_none(first_value(row, "startDate", "stdate", "effectiveStartDate")),
        end_date=strip_or_none(first_value(row, "endDate", "eddate", "effectiveEndDate")),
        days=strip_or_none(first_value(row, "week", "days", "dayOfWeek")),
        season=strip_or_none(first_value(row, "season", "seasonCode")),
        raw=dict(row),
    )


def _build_service_destination(row: Mapping[str, Any]) -> ServiceDestination:
    return ServiceDestination(
        airport_code=strip_or_none(first_value(row, "airportCode", "airport_code", "iata")),
        airport_name=strip_or_none(first_value(row, "airport", "airportName", "airportNm")),
        city_code=strip_or_none(first_value(row, "cityCode", "city_code")),
        city_name=strip_or_none(first_value(row, "city", "cityName", "cityNm")),
        country_name=strip_or_none(first_value(row, "country", "countryName", "countryNm")),
        coordinate=coordinate_from_mapping(row),
        raw=dict(row),
    )


def _build_facility(row: Mapping[str, Any]) -> AirportFacility:
    return AirportFacility(
        provider=Provider.IIAC,
        airport_code="ICN",
        terminal=strip_or_none(first_value(row, "terminal", "terminalid", "terno")),
        name=str(first_value(row, "facility_nm", "facilityName", "name", "shopName") or ""),
        category=strip_or_none(first_value(row, "category", "lclas", "facilityType")),
        floor=strip_or_none(first_value(row, "floor", "floorInfo")),
        location=strip_or_none(first_value(row, "location", "loc", "area")),
        business_hours=strip_or_none(first_value(row, "operTime", "businessHours", "hours")),
        telephone=strip_or_none(first_value(row, "tel", "telephone", "phone")),
        coordinate=coordinate_from_mapping(row),
        raw=dict(row),
    )


def _validate_path_part(value: str) -> None:
    if not _SAFE_PATH_PART.fullmatch(value):
        raise ValueError(f"unsafe IIAC service path component: {value!r}")
