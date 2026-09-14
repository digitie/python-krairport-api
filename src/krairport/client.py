"""사용자용 통합 클라이언트."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from datetime import date
from typing import Any, TypeVar

from krairport._http import SessionLike
from krairport._ratelimit import AsyncTokenBucket
from krairport._routing import provider_for_airport
from krairport.airports import get_airport, list_airports, nearest_airport
from krairport.config import KrairportConfig
from krairport.debug import DebugRun, debug_call
from krairport.enums import Provider
from krairport.geo import Coordinate, CoordinateTuple
from krairport.models import (
    AircraftAssignment,
    AirportFacility,
    AirportMetadata,
    ArrivalCongestion,
    BusRoute,
    Flight,
    FlightSchedule,
    PaginatedResult,
    ParkingAreaStatus,
    ParkingFee,
    PassengerForecast,
    ServiceDestination,
    TaxiStatus,
    WorldWeather,
)
from krairport.providers import IiacClient, KacClient
from krairport.types import DirectionLike, ProviderLike

T = TypeVar("T")




class KrairportClient:
    """KAC와 IIAC 공항 API의 비동기 통합 클라이언트."""

    def __init__(
        self,
        kac_service_key: str | None = None,
        iiac_service_key: str | None = None,
        *,
        timeout: float = 10.0,
        retries: int = 3,
        max_rps: float = 5.0,
        rate_limiter: AsyncTokenBucket | None = None,
        session: SessionLike | None = None,
        kac_client: KacClient | None = None,
        iiac_client: IiacClient | None = None,
    ) -> None:
        self.rate_limiter = rate_limiter if rate_limiter is not None else AsyncTokenBucket(max_rps)
        self.config = KrairportConfig(
            kac_service_key=kac_service_key,
            iiac_service_key=iiac_service_key,
            timeout=timeout,
            retries=retries,
        )
        self.kac = kac_client or KacClient(
            kac_service_key,
            session=session,
            timeout=timeout,
            retries=retries,
            rate_limiter=self.rate_limiter,
        )
        self.iiac = iiac_client or IiacClient(
            iiac_service_key,
            session=session,
            timeout=timeout,
            retries=retries,
            rate_limiter=self.rate_limiter,
        )

        self.kac._http.rate_limiter = self.rate_limiter
        self.iiac._http.rate_limiter = self.rate_limiter

    @classmethod
    def from_env(
        cls,
        *,
        service_key_name: str = "DATA_GO_KR_SERVICE_KEY",
        env_file: str | None = None,
        **kwargs: Any,
    ) -> KrairportClient:
        config = KrairportConfig.from_env(
            kac_service_key=kwargs.pop("kac_service_key", None),
            iiac_service_key=kwargs.pop("iiac_service_key", None),
            service_key_name=service_key_name,
            env_file=env_file,
            timeout=kwargs.pop("timeout", None),
            retries=kwargs.pop("retries", None),
        )
        return cls(
            kac_service_key=config.kac_service_key,
            iiac_service_key=config.iiac_service_key,
            timeout=config.timeout,
            retries=config.retries,
            **kwargs,
        )

    async def __aenter__(self) -> KrairportClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        for provider_client in (self.kac, self.iiac):
            close = getattr(provider_client, "aclose", None)
            if callable(close):
                await close()

    async def departures(
        self,
        *,
        airport_code: str,
        searchday: str | date | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        flight_id: str | None = None,
        flight_unique_id: str | None = None,
        airline_code: str | None = None,
        line: str | None = None,
        counterpart_airport_code: str | None = None,
        lang: str = "K",
        use_detailed: bool | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> list[Flight]:
        provider = provider_for_airport(airport_code)
        searchday_text = _date_to_yyyymmdd(searchday)
        if provider is Provider.IIAC:
            return await self.iiac.departures(
                airport_code=airport_code,
                searchday=searchday_text,
                from_time=from_time,
                to_time=to_time,
                flight_id=flight_id,
                flight_unique_id=flight_unique_id,
                airline_code=airline_code,
                counterpart_airport_code=counterpart_airport_code,
                lang=lang,
                detailed=_use_detailed(searchday_text, use_detailed),
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return await self.kac.departures(
            airport_code=airport_code,
            searchday=searchday_text,
            from_time=from_time,
            to_time=to_time,
            flight_id=flight_id,
            flight_unique_id=flight_unique_id,
            line=line,
            arr_airport_code=counterpart_airport_code,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def arrivals(
        self,
        *,
        airport_code: str,
        searchday: str | date | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        flight_id: str | None = None,
        flight_unique_id: str | None = None,
        airline_code: str | None = None,
        line: str | None = None,
        counterpart_airport_code: str | None = None,
        lang: str = "K",
        use_detailed: bool | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> list[Flight]:
        provider = provider_for_airport(airport_code)
        searchday_text = _date_to_yyyymmdd(searchday)
        if provider is Provider.IIAC:
            return await self.iiac.arrivals(
                airport_code=airport_code,
                searchday=searchday_text,
                from_time=from_time,
                to_time=to_time,
                flight_id=flight_id,
                flight_unique_id=flight_unique_id,
                airline_code=airline_code,
                counterpart_airport_code=counterpart_airport_code,
                lang=lang,
                detailed=_use_detailed(searchday_text, use_detailed),
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return await self.kac.arrivals(
            airport_code=airport_code,
            searchday=searchday_text,
            from_time=from_time,
            to_time=to_time,
            flight_id=flight_id,
            flight_unique_id=flight_unique_id,
            line=line,
            dep_airport_code=counterpart_airport_code,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

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
        return await self.kac.aircraft_assignments(
            airport_code=airport_code,
            sch_st_time=sch_st_time,
            sch_ed_time=sch_ed_time,
            flight_id=flight_id,
            flight_unique_id=flight_unique_id,
            aircraft_registration=aircraft_registration,
            aircraft_type=aircraft_type,
            line=line,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def parking_fees(self, *, airport_code: str | None = None) -> list[ParkingFee]:
        return await self.kac.parking_fees(airport_code=airport_code)

    async def parking_status(
        self,
        *,
        airport_code: str = "ICN",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ParkingAreaStatus]:
        if provider_for_airport(airport_code) is Provider.IIAC:
            return await self.iiac.parking_status(
                airport_code=airport_code,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return await self.kac.parking_status(
            airport_code=airport_code,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def arrival_congestion(
        self,
        *,
        airport_code: str = "ICN",
        terminal: str | None = None,
        airport: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ArrivalCongestion]:
        return await self.iiac.arrival_congestion(
            airport_code=airport_code,
            terminal=terminal,
            airport=airport,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def passenger_forecast(
        self,
        *,
        airport_code: str = "ICN",
        selectdate: int = 0,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[PassengerForecast]:
        return await self.iiac.passenger_forecast(
            airport_code=airport_code,
            selectdate=selectdate,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def flight_schedules(
        self,
        *,
        airport_code: str,
        direction: DirectionLike,
        counterpart_airport_code: str | None = None,
        sch_date: str | None = None,
        airline_code: str | None = None,
        flight_id: str | None = None,
        international: bool = False,
        lang: str = "K",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[FlightSchedule]:
        if provider_for_airport(airport_code) is Provider.IIAC:
            return await self.iiac.flight_schedules(
                direction=direction,
                airport_code=airport_code,
                counterpart_airport_code=counterpart_airport_code,
                airline_code=airline_code,
                flight_id=flight_id,
                lang=lang,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return await self.kac.flight_schedules(
            direction=direction,
            airport_code=airport_code,
            counterpart_airport_code=counterpart_airport_code,
            sch_date=sch_date,
            airline_code=airline_code,
            flight_id=flight_id,
            international=international,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def airport_facilities(
        self,
        *,
        airport_code: str,
        facility_name: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[AirportFacility]:
        if provider_for_airport(airport_code) is Provider.IIAC:
            return await self.iiac.facilities(
                airport_code=airport_code,
                facility_name=facility_name,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return await self.kac.airport_facilities(
            airport_code=airport_code,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def bus_routes(
        self,
        *,
        airport_code: str,
        area: str = "1",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[BusRoute]:
        if provider_for_airport(airport_code) is Provider.IIAC:
            return await self.iiac.bus_routes(
                airport_code=airport_code,
                area=area,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return await self.kac.airport_buses(
            airport_code=airport_code,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def taxi_status(
        self,
        *,
        airport_code: str = "ICN",
        terminal: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[TaxiStatus]:
        if provider_for_airport(airport_code) is Provider.IIAC:
            return await self.iiac.taxi_status(
                airport_code=airport_code,
                terminal=terminal,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        if airport_code.upper() == "CJU":
            return await self.kac.jeju_taxi_wait(page_no=page_no, num_of_rows=num_of_rows)
        return []

    async def world_weather(
        self,
        *,
        direction: DirectionLike,
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
        return await self.iiac.world_weather(
            direction=direction,
            airport_code=airport_code,
            from_time=from_time,
            to_time=to_time,
            airport=airport,
            flight_id=flight_id,
            airline_code=airline_code,
            lang=lang,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def service_destinations(
        self,
        *,
        airport_code: str | None = None,
        lang: str = "K",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ServiceDestination]:
        return await self.iiac.service_destinations(
            airport_code=airport_code,
            lang=lang,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def kac_raw_items(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return await self.kac.raw_items(service, operation, params)

    async def kac_flight_status_detail_raw_items(
        self,
        *,
        airport_code: str,
        flight_date: str,
        page: int = 1,
        per_page: int = 1000,
    ) -> list[dict[str, Any]]:
        """KAC ODCloud 상세 운항정보(FlightStatusListDTL)의 raw item 목록을 반환합니다."""

        return await self.kac.flight_status_detail_raw_items(
            airport_code=airport_code,
            flight_date=flight_date,
            page=page,
            per_page=per_page,
        )

    async def iiac_raw_items(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return await self.iiac.raw_items(service, operation, params)

    def airport_metadata(self, airport_code: str) -> AirportMetadata:
        return get_airport(airport_code)

    def airports(
        self,
        *,
        provider: ProviderLike | None = None,
        active: bool | None = None,
    ) -> tuple[AirportMetadata, ...]:
        return list_airports(provider=provider, active=active)

    def nearest_airport(
        self,
        coordinate: Coordinate | CoordinateTuple,
        *,
        provider: ProviderLike | None = None,
        active: bool | None = True,
    ) -> AirportMetadata | None:
        return nearest_airport(coordinate, provider=provider, active=active)

    async def iter_pages(
        self,
        fetch_page: Callable[..., Awaitable[list[T]]],
        *args: Any,
        page_no: int = 1,
        num_of_rows: int = 100,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[PaginatedResult[T]]:
        """공통 page_no/num_of_rows 계약의 비동기 페이지 순회자."""

        if page_no <= 0:
            raise ValueError("page_no must be greater than 0")
        if num_of_rows <= 0:
            raise ValueError("num_of_rows must be greater than 0")
        page = page_no
        scanned_pages = 0
        while True:
            items = await fetch_page(*args, page_no=page, num_of_rows=num_of_rows, **kwargs)
            scanned_pages += 1
            total = ((page - page_no) * num_of_rows) + len(items)
            yield PaginatedResult(total=total, page=page, size=num_of_rows, items=list(items))
            if max_pages is not None and scanned_pages >= max_pages:
                return
            if len(items) < num_of_rows:
                return
            page += 1

    async def debug(self, function_name: str, **input_data: Any) -> DebugRun:
        """디버그 UI가 저장 가능한 실행 결과를 만들도록 public 함수를 실행합니다."""

        return (await debug_call(self, function_name, **input_data))


    async def debug_departures(self, **input_data: Any) -> DebugRun:
        """`departures()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("departures", **input_data))


    async def debug_arrivals(self, **input_data: Any) -> DebugRun:
        """`arrivals()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("arrivals", **input_data))


    async def debug_aircraft_assignments(self, **input_data: Any) -> DebugRun:
        """`aircraft_assignments()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("aircraft_assignments", **input_data))


    async def debug_parking_fees(self, **input_data: Any) -> DebugRun:
        """`parking_fees()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("parking_fees", **input_data))


    async def debug_parking_status(self, **input_data: Any) -> DebugRun:
        """`parking_status()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("parking_status", **input_data))


    async def debug_arrival_congestion(self, **input_data: Any) -> DebugRun:
        """`arrival_congestion()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("arrival_congestion", **input_data))


    async def debug_passenger_forecast(self, **input_data: Any) -> DebugRun:
        """`passenger_forecast()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("passenger_forecast", **input_data))


    async def debug_flight_schedules(self, **input_data: Any) -> DebugRun:
        """`flight_schedules()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("flight_schedules", **input_data))


    async def debug_airport_facilities(self, **input_data: Any) -> DebugRun:
        """`airport_facilities()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("airport_facilities", **input_data))


    async def debug_bus_routes(self, **input_data: Any) -> DebugRun:
        """`bus_routes()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("bus_routes", **input_data))


    async def debug_taxi_status(self, **input_data: Any) -> DebugRun:
        """`taxi_status()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("taxi_status", **input_data))


    async def debug_world_weather(self, **input_data: Any) -> DebugRun:
        """`world_weather()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("world_weather", **input_data))


    async def debug_service_destinations(self, **input_data: Any) -> DebugRun:
        """`service_destinations()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("service_destinations", **input_data))


    async def debug_kac_raw_items(self, **input_data: Any) -> DebugRun:
        """`kac_raw_items()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("kac_raw_items", **input_data))


    async def debug_iiac_raw_items(self, **input_data: Any) -> DebugRun:
        """`iiac_raw_items()` 실행 결과를 fixture 후보로 반환합니다."""

        return (await self.debug("iiac_raw_items", **input_data))




def _date_to_yyyymmdd(value: str | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    return value


def _use_detailed(searchday: str | None, explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    if searchday is None:
        return False
    return searchday != date.today().strftime("%Y%m%d")
