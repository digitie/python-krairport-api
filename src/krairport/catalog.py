"""지원 API 카탈로그."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from krairport.enums import Provider, normalize_provider
from krairport.types import ProviderLike

_DATA_GO_KR_SEARCH = "https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword="
_SERVICE_KEY_URLS = {
    "kac_status_of_flights": "https://www.data.go.kr/data/15113771/openapi.do",
    "kac_flight_status_apl_list": "https://www.data.go.kr/data/15144867/openapi.do",
    "kac_airport_parking_fee": "https://www.data.go.kr/data/15038474/openapi.do",
    "kac_airport_parking_congestion": "https://www.data.go.kr/data/15063437/openapi.do",
    "kac_airport_code_list": "https://www.data.go.kr/data/15000126/openapi.do",
    "kac_flight_schedule_list": "https://www.data.go.kr/data/15000126/openapi.do",
    "kac_airport_facilities": (
        _DATA_GO_KR_SEARCH + "%ED%95%9C%EA%B5%AD%EA%B3%B5%ED%95%AD%EA%B3%B5%EC%82%AC"
        "%20AirportFacilities"
    ),
    "kac_airport_bus_info": "https://www.data.go.kr/data/15040594/openapi.do",
    "kac_taxi_wait_info": (
        _DATA_GO_KR_SEARCH + "%ED%95%9C%EA%B5%AD%EA%B3%B5%ED%95%AD%EA%B3%B5%EC%82%AC"
        "%20getJejuTaxiWaitInfo"
    ),
    "iiac_status_of_passenger_flights_de_odp": (
        "https://www.data.go.kr/data/15112968/openapi.do"
    ),
    "iiac_status_of_passenger_flights_odp": "https://www.data.go.kr/data/15095093/openapi.do",
    "iiac_status_of_parking": "https://www.data.go.kr/data/15095047/openapi.do",
    "iiac_status_of_arrivals": "https://www.data.go.kr/data/15095061/openapi.do",
    "iiac_passenger_notice_kr": "https://www.data.go.kr/data/15095066/openapi.do",
    "iiac_pax_flt_sched": "https://www.data.go.kr/data/15095059/openapi.do",
    "iiac_status_of_facility": "https://www.data.go.kr/data/15095043/openapi.do",
    "iiac_bus_information": "https://www.data.go.kr/data/15095045/openapi.do",
    "iiac_status_of_taxi": "https://www.data.go.kr/data/15095062/openapi.do",
    "iiac_status_of_passenger_world_weather_info": (
        "https://www.data.go.kr/data/15095086/openapi.do"
    ),
    "iiac_status_of_srv_destinations": "https://www.data.go.kr/data/15095067/openapi.do",
}


@dataclass(frozen=True)
class ApiCatalogItem:
    """디버그 UI와 문서에서 함께 쓰는 endpoint 카탈로그 항목."""

    function: str
    provider: Provider
    dataset: str
    dataset_name: str
    service: str
    operation: str
    endpoint: str
    response_format: str
    notes: str = ""

    @property
    def service_key_url(self) -> str:
        """공공데이터포털 활용신청 또는 검색 페이지 URL을 반환합니다."""

        return _SERVICE_KEY_URLS.get(self.dataset, _DATA_GO_KR_SEARCH + self.dataset)

    def to_dict(self) -> dict[str, Any]:
        """Streamlit 표와 JSON 표시가 바로 사용할 수 있는 dict로 변환합니다."""

        data = asdict(self)
        data["provider"] = str(self.provider)
        data["service_key_url"] = self.service_key_url
        return data


API_CATALOG: tuple[ApiCatalogItem, ...] = (
    ApiCatalogItem(
        function="departures",
        provider=Provider.KAC,
        dataset="kac_status_of_flights",
        dataset_name="한국공항공사 실시간 항공운항 현황 상세 조회",
        service="StatusOfFlights",
        operation="getDepFlightStatusList",
        endpoint="https://openapi.airport.co.kr/service/rest/StatusOfFlights/getDepFlightStatusList",
        response_format="xml",
        notes="ICN을 제외한 KAC 공항 출발편",
    ),
    ApiCatalogItem(
        function="arrivals",
        provider=Provider.KAC,
        dataset="kac_status_of_flights",
        dataset_name="한국공항공사 실시간 항공운항 현황 상세 조회",
        service="StatusOfFlights",
        operation="getArrFlightStatusList",
        endpoint="https://openapi.airport.co.kr/service/rest/StatusOfFlights/getArrFlightStatusList",
        response_format="xml",
        notes="ICN을 제외한 KAC 공항 도착편",
    ),
    ApiCatalogItem(
        function="departures",
        provider=Provider.IIAC,
        dataset="iiac_status_of_passenger_flights_de_odp",
        dataset_name="인천국제공항공사 여객기 운항 현황 상세 조회 서비스",
        service="StatusOfPassengerFlightsDeOdp",
        operation="getPassengerDeparturesDeOdp",
        endpoint=(
            "https://apis.data.go.kr/B551177/StatusOfPassengerFlightsDeOdp/"
            "getPassengerDeparturesDeOdp"
        ),
        response_format="json",
        notes="use_detailed=True 또는 조회일이 오늘이 아닐 때 사용",
    ),
    ApiCatalogItem(
        function="arrivals",
        provider=Provider.IIAC,
        dataset="iiac_status_of_passenger_flights_de_odp",
        dataset_name="인천국제공항공사 여객기 운항 현황 상세 조회 서비스",
        service="StatusOfPassengerFlightsDeOdp",
        operation="getPassengerArrivalsDeOdp",
        endpoint=(
            "https://apis.data.go.kr/B551177/StatusOfPassengerFlightsDeOdp/"
            "getPassengerArrivalsDeOdp"
        ),
        response_format="json",
        notes="use_detailed=True 또는 조회일이 오늘이 아닐 때 사용",
    ),
    ApiCatalogItem(
        function="departures",
        provider=Provider.IIAC,
        dataset="iiac_status_of_passenger_flights_odp",
        dataset_name="인천국제공항공사 여객기 운항현황(당일)",
        service="StatusOfPassengerFlightsOdp",
        operation="getPassengerDeparturesOdp",
        endpoint=(
            "https://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/"
            "getPassengerDeparturesOdp"
        ),
        response_format="json",
        notes="use_detailed=False 또는 오늘 운항 조회",
    ),
    ApiCatalogItem(
        function="arrivals",
        provider=Provider.IIAC,
        dataset="iiac_status_of_passenger_flights_odp",
        dataset_name="인천국제공항공사 여객기 운항현황(당일)",
        service="StatusOfPassengerFlightsOdp",
        operation="getPassengerArrivalsOdp",
        endpoint=(
            "https://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/"
            "getPassengerArrivalsOdp"
        ),
        response_format="json",
        notes="use_detailed=False 또는 오늘 운항 조회",
    ),
    ApiCatalogItem(
        function="aircraft_assignments",
        provider=Provider.KAC,
        dataset="kac_flight_status_apl_list",
        dataset_name="한국공항공사 전국공항 실시간 항공기 기종 및 등록번호 정보",
        service="FlightStatusAPLList",
        operation="getFlightStatusAPLList",
        endpoint=(
            "https://openapi.airport.co.kr/service/rest/FlightStatusAPLList/"
            "getFlightStatusAPLList"
        ),
        response_format="xml",
    ),
    ApiCatalogItem(
        function="parking_fees",
        provider=Provider.KAC,
        dataset="kac_airport_parking_fee",
        dataset_name="한국공항공사 전국공항 주차요금",
        service="AirportParkingFee",
        operation="parkingfee",
        endpoint="https://openapi.airport.co.kr/service/rest/AirportParkingFee/parkingfee",
        response_format="xml",
    ),
    ApiCatalogItem(
        function="parking_status",
        provider=Provider.KAC,
        dataset="kac_airport_parking_congestion",
        dataset_name="한국공항공사 전국공항 주차장 혼잡도",
        service="AirportParkingCongestion",
        operation="airportParkingCongestionRT",
        endpoint=(
            "https://openapi.airport.co.kr/service/rest/AirportParkingCongestion/"
            "airportParkingCongestionRT"
        ),
        response_format="xml",
        notes="ICN을 제외한 KAC 공항 주차 현황",
    ),
    ApiCatalogItem(
        function="parking_status",
        provider=Provider.IIAC,
        dataset="iiac_status_of_parking",
        dataset_name="인천국제공항공사 주차 정보",
        service="StatusOfParking",
        operation="getTrackingParking",
        endpoint="https://apis.data.go.kr/B551177/StatusOfParking/getTrackingParking",
        response_format="json",
        notes="ICN 주차 현황",
    ),
    ApiCatalogItem(
        function="arrival_congestion",
        provider=Provider.IIAC,
        dataset="iiac_status_of_arrivals",
        dataset_name="인천국제공항공사 입국장 현황 정보 서비스",
        service="StatusOfArrivals",
        operation="getArrivalsCongestion",
        endpoint="https://apis.data.go.kr/B551177/StatusOfArrivals/getArrivalsCongestion",
        response_format="json",
    ),
    ApiCatalogItem(
        function="passenger_forecast",
        provider=Provider.IIAC,
        dataset="iiac_passenger_notice_kr",
        dataset_name="인천국제공항공사 혼잡도 예고-출입국장별",
        service="PassengerNoticeKR",
        operation="getfPassengerNoticeIKR",
        endpoint="https://apis.data.go.kr/B551177/PassengerNoticeKR/getfPassengerNoticeIKR",
        response_format="json",
    ),
    ApiCatalogItem(
        function="airport_codes",
        provider=Provider.KAC,
        dataset="kac_airport_code_list",
        dataset_name="한국공항공사 전국공항 코드 정보",
        service="AirportCodeList",
        operation="getAirportCodeList",
        endpoint="https://openapi.airport.co.kr/service/rest/AirportCodeList/getAirportCodeList",
        response_format="xml",
    ),
    ApiCatalogItem(
        function="flight_schedules",
        provider=Provider.KAC,
        dataset="kac_flight_schedule_list",
        dataset_name="한국공항공사 정기 항공 운항 스케줄",
        service="FlightScheduleList",
        operation="getDflightScheduleList / getIflightScheduleList",
        endpoint="https://openapi.airport.co.kr/service/rest/FlightScheduleList/{operation}",
        response_format="xml",
        notes="international 값에 따라 국내선/국제선 operation 선택",
    ),
    ApiCatalogItem(
        function="flight_schedules",
        provider=Provider.IIAC,
        dataset="iiac_pax_flt_sched",
        dataset_name="인천국제공항공사 여객기 정기 운항 스케줄",
        service="PaxFltSched",
        operation="getPaxFltSchedArrivals / getPaxFltSchedDepartures",
        endpoint="https://apis.data.go.kr/B551177/PaxFltSched/{operation}",
        response_format="json",
        notes="direction 값에 따라 arrivals/departures operation 선택",
    ),
    ApiCatalogItem(
        function="airport_facilities",
        provider=Provider.KAC,
        dataset="kac_airport_facilities",
        dataset_name="한국공항공사 전국공항 시설 정보",
        service="AirportFacilities",
        operation="getAirportFacilities",
        endpoint=(
            "https://openapi.airport.co.kr/service/rest/AirportFacilities/"
            "getAirportFacilities"
        ),
        response_format="xml",
    ),
    ApiCatalogItem(
        function="airport_facilities",
        provider=Provider.IIAC,
        dataset="iiac_status_of_facility",
        dataset_name="인천국제공항공사 편의시설 정보",
        service="StatusOfFacility",
        operation="getFacilityKR",
        endpoint="https://apis.data.go.kr/B551177/StatusOfFacility/getFacilityKR",
        response_format="json",
    ),
    ApiCatalogItem(
        function="bus_routes",
        provider=Provider.KAC,
        dataset="kac_airport_bus_info",
        dataset_name="한국공항공사 전국공항 버스 정보",
        service="AirportBusInfo",
        operation="businfo",
        endpoint="https://openapi.airport.co.kr/service/rest/AirportBusInfo/businfo",
        response_format="xml",
    ),
    ApiCatalogItem(
        function="bus_routes",
        provider=Provider.IIAC,
        dataset="iiac_bus_information",
        dataset_name="인천국제공항공사 버스 정보",
        service="BusInformation",
        operation="getBusInfo",
        endpoint="https://apis.data.go.kr/B551177/BusInformation/getBusInfo",
        response_format="json",
    ),
    ApiCatalogItem(
        function="taxi_status",
        provider=Provider.KAC,
        dataset="kac_taxi_wait_info",
        dataset_name="한국공항공사 제주공항 택시 대기 정보",
        service="taxiWaitInfo",
        operation="getJejuTaxiWaitInfo",
        endpoint="https://openapi.airport.co.kr/service/rest/taxiWaitInfo/getJejuTaxiWaitInfo",
        response_format="xml",
        notes="KAC 경로는 CJU 택시 대기 정보만 반환",
    ),
    ApiCatalogItem(
        function="taxi_status",
        provider=Provider.IIAC,
        dataset="iiac_status_of_taxi",
        dataset_name="인천국제공항공사 택시 출차 현황",
        service="StatusOfTaxi",
        operation="getTaxiStatus",
        endpoint="https://apis.data.go.kr/B551177/StatusOfTaxi/getTaxiStatus",
        response_format="json",
    ),
    ApiCatalogItem(
        function="world_weather",
        provider=Provider.IIAC,
        dataset="iiac_status_of_passenger_world_weather_info",
        dataset_name="인천국제공항공사 여객기 운항 세계공항 날씨 정보",
        service="StatusOfPassengerWorldWeatherInfo",
        operation="getPassengerArrivalsWorldWeather / getPassengerDeparturesWorldWeather",
        endpoint="https://apis.data.go.kr/B551177/StatusOfPassengerWorldWeatherInfo/{operation}",
        response_format="json",
    ),
    ApiCatalogItem(
        function="service_destinations",
        provider=Provider.IIAC,
        dataset="iiac_status_of_srv_destinations",
        dataset_name="인천국제공항공사 취항 도시 및 공항 정보",
        service="StatusOfSrvDestinations",
        operation="getServiceDestinationInfo",
        endpoint=(
            "https://apis.data.go.kr/B551177/StatusOfSrvDestinations/"
            "getServiceDestinationInfo"
        ),
        response_format="json",
    ),
)


def api_catalog(
    function_name: str | None = None,
    *,
    provider: ProviderLike | None = None,
) -> tuple[ApiCatalogItem, ...]:
    """지원 API 카탈로그를 함수명과 provider로 필터링해 반환합니다."""

    provider_value = normalize_provider(provider) if provider is not None else None
    return tuple(
        item
        for item in API_CATALOG
        if (function_name is None or item.function == function_name)
        and (provider_value is None or item.provider is provider_value)
    )
