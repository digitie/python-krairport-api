"""User-facing unified client."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

from pykrairport._http import SessionLike
from pykrairport._routing import provider_for_airport
from pykrairport.models import (
    AircraftAssignment,
    ArrivalCongestion,
    Flight,
    ParkingAreaStatus,
    ParkingFee,
    PassengerForecast,
)
from pykrairport.providers import IiacClient, KacClient


class KrairportClient:
    """Unified client for Korean airport public APIs."""

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
        if provider == "iiac":
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
        if provider == "iiac":
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
        """IIAC 인천공항 주차현황을 조회합니다."""

        return self.iiac.parking_status(
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
