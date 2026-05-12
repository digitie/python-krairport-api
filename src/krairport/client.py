"""사용자용 통합 클라이언트."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import date
from typing import Any

from pykrtour import PlaceCoordinate

from krairport._http import SessionLike
from krairport._routing import provider_for_airport
from krairport.airports import get_airport, list_airports, nearest_airport
from krairport.enums import Provider
from krairport.models import (
    AircraftAssignment,
    AirportCode,
    AirportFacility,
    AirportMetadata,
    ArrivalCongestion,
    BusRoute,
    Flight,
    FlightSchedule,
    ParkingAreaStatus,
    ParkingFee,
    PassengerForecast,
    ServiceDestination,
    TaxiStatus,
    WorldWeather,
)
from krairport.providers import IiacClient, KacClient
from krairport.types import DirectionLike, ProviderLike


class KrairportClient:
    """한국 공항 공공 API 통합 클라이언트."""

    def __init__(
        self,
        kac_service_key: str | None = None,
        iiac_service_key: str | None = None,
        *,
        timeout: float = 10.0,
        retries: int = 3,
        session: SessionLike | None = None,
        kac_client: KacClient | None = None,
        iiac_client: IiacClient | None = None,
    ) -> None:
        self.kac = kac_client or KacClient(
            kac_service_key,
            session=session,
            timeout=timeout,
            retries=retries,
        )
        self.iiac = iiac_client or IiacClient(
            iiac_service_key,
            session=session,
            timeout=timeout,
            retries=retries,
        )

    @classmethod
    def from_env(
        cls,
        *,
        kac_name: str = "KAC_SERVICE_KEY",
        iiac_name: str = "IIAC_SERVICE_KEY",
        **kwargs: Any,
    ) -> KrairportClient:
        return cls(
            kac_service_key=os.getenv(kac_name),
            iiac_service_key=os.getenv(iiac_name),
            **kwargs,
        )

    def departures(
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
        """출발 항공편을 공항코드에 맞는 공급자에서 조회합니다."""

        provider = provider_for_airport(airport_code)
        searchday_text = _date_to_yyyymmdd(searchday)
        if provider is Provider.IIAC:
            return self.iiac.departures(
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
        return self.kac.departures(
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

    def arrivals(
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
        """도착 항공편을 공항코드에 맞는 공급자에서 조회합니다."""

        provider = provider_for_airport(airport_code)
        searchday_text = _date_to_yyyymmdd(searchday)
        if provider is Provider.IIAC:
            return self.iiac.arrivals(
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
        return self.kac.arrivals(
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
        """KAC 항공기 등록번호/기종 정보를 조회합니다."""

        return self.kac.aircraft_assignments(
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

    def parking_fees(self, *, airport_code: str | None = None) -> list[ParkingFee]:
        """KAC 공항별 주차요금 정보를 조회합니다."""

        return self.kac.parking_fees(airport_code=airport_code)

    def parking_status(
        self,
        *,
        airport_code: str = "ICN",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ParkingAreaStatus]:
        """공항별 주차현황을 조회합니다.

        `ICN`은 IIAC, 그 외 KAC 공항은 KAC 주차 혼잡도 API로 조회합니다.
        """

        if provider_for_airport(airport_code) is Provider.IIAC:
            return self.iiac.parking_status(
                airport_code=airport_code,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return self.kac.parking_status(
            airport_code=airport_code,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def arrival_congestion(
        self,
        *,
        airport_code: str = "ICN",
        terminal: str | None = None,
        airport: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ArrivalCongestion]:
        """IIAC 인천공항 입국장 혼잡도 정보를 조회합니다."""

        return self.iiac.arrival_congestion(
            airport_code=airport_code,
            terminal=terminal,
            airport=airport,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def passenger_forecast(
        self,
        *,
        airport_code: str = "ICN",
        selectdate: int = 0,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[PassengerForecast]:
        """IIAC 인천공항 승객예고 정보를 조회합니다."""

        return self.iiac.passenger_forecast(
            airport_code=airport_code,
            selectdate=selectdate,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def airport_codes(
        self,
        *,
        code: str | None = None,
        korean_name: str | None = None,
        english_name: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[AirportCode]:
        """KAC 공항코드 목록을 조회합니다."""

        return self.kac.airport_codes(
            code=code,
            korean_name=korean_name,
            english_name=english_name,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def flight_schedules(
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
        """정기 운항편 스케줄을 조회합니다."""

        if provider_for_airport(airport_code) is Provider.IIAC:
            return self.iiac.flight_schedules(
                direction=direction,
                airport_code=airport_code,
                counterpart_airport_code=counterpart_airport_code,
                airline_code=airline_code,
                flight_id=flight_id,
                lang=lang,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return self.kac.flight_schedules(
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

    def airport_facilities(
        self,
        *,
        airport_code: str,
        facility_name: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[AirportFacility]:
        """공항 시설/상업시설 정보를 조회합니다."""

        if provider_for_airport(airport_code) is Provider.IIAC:
            return self.iiac.facilities(
                airport_code=airport_code,
                facility_name=facility_name,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return self.kac.airport_facilities(
            airport_code=airport_code,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def bus_routes(
        self,
        *,
        airport_code: str,
        area: str = "1",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[BusRoute]:
        """공항 버스 정보를 조회합니다."""

        if provider_for_airport(airport_code) is Provider.IIAC:
            return self.iiac.bus_routes(
                airport_code=airport_code,
                area=area,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        return self.kac.airport_buses(
            airport_code=airport_code,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def taxi_status(
        self,
        *,
        airport_code: str = "ICN",
        terminal: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[TaxiStatus]:
        """택시 대기/출차 정보를 조회합니다.

        `ICN`은 IIAC 택시출차, `CJU`는 KAC 제주 택시대기 정보를 사용합니다.
        """

        if provider_for_airport(airport_code) is Provider.IIAC:
            return self.iiac.taxi_status(
                airport_code=airport_code,
                terminal=terminal,
                page_no=page_no,
                num_of_rows=num_of_rows,
            )
        if airport_code.upper() == "CJU":
            return self.kac.jeju_taxi_wait(page_no=page_no, num_of_rows=num_of_rows)
        return []

    def world_weather(
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
        """IIAC 여객편 상대 공항 기상정보를 조회합니다."""

        return self.iiac.world_weather(
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

    def service_destinations(
        self,
        *,
        airport_code: str | None = None,
        lang: str = "K",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[ServiceDestination]:
        """IIAC 취항도시 현황을 조회합니다."""

        return self.iiac.service_destinations(
            airport_code=airport_code,
            lang=lang,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def kac_raw_items(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """KAC 공식 REST 엔드포인트의 raw item 목록을 반환합니다."""

        return self.kac.raw_items(service, operation, params)

    def iiac_raw_items(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """IIAC B551177 공식 REST 엔드포인트의 raw item 목록을 반환합니다."""

        return self.iiac.raw_items(service, operation, params)

    def airport_metadata(self, airport_code: str) -> AirportMetadata:
        """번들 공항 메타데이터를 조회합니다."""

        return get_airport(airport_code)

    def airports(
        self,
        *,
        provider: ProviderLike | None = None,
        active: bool | None = None,
    ) -> tuple[AirportMetadata, ...]:
        """번들 공항 메타데이터 목록을 반환합니다."""

        return list_airports(provider=provider, active=active)

    def nearest_airport(
        self,
        coordinate: PlaceCoordinate,
        *,
        provider: ProviderLike | None = None,
        active: bool | None = True,
    ) -> AirportMetadata | None:
        """`PlaceCoordinate` 기준 가장 가까운 번들 공항 메타데이터를 반환합니다."""

        return nearest_airport(coordinate, provider=provider, active=active)


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
