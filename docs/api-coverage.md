# API 커버리지

확인 기준일: 2026-04-30

이 문서는 KAC/IIAC 공식 목록과 `krairport` 구현 범위를 대조한 기록입니다. 목적은 "빠진 API"를 다시 손으로 훑는 일을 줄이고, typed 모델로 안정화된 API와 raw fallback으로 접근 가능한 API를 구분하는 것입니다.

공식 확인 출처:

- KAC 서비스 목록: <https://openapi.airport.co.kr/service>
- IIAC 공공데이터포털 B551177 계열: <https://www.data.go.kr>
- IIAC 2026년 변경 공지: `FlightClosingInfoSpot`, `statusOfFltacdmmlstnAirTrafficPublic`

## 요약

`0.1.0` 초기 구현 이후 추가로 확인한 누락 API:

- KAC: 공항코드, 정기 운항스케줄, 주차 혼잡도/실시간 주차, 공항시설, 공항버스, 제주 택시대기
- IIAC: 정기 운항스케줄, 취항도시, 기상, 택시출차, 버스정보, 상업시설
- IIAC 변경/미모델링 API: 주차요금, 취항 항공사, 화물기 운항, 옥외 대기질, Flight Closing, ACDM 계열은 raw 접근으로 먼저 열어 둠
- 기타 KAC/IIAC 공식 엔드포인트: typed 모델이 아직 없는 경우에도 `kac_raw_items()` / `iiac_raw_items()`로 접근 가능

## Typed 지원 API

| Public method | Provider | Endpoint |
|---|---|---|
| `departures()` | KAC | `StatusOfFlights/getDepFlightStatusList` |
| `arrivals()` | KAC | `StatusOfFlights/getArrFlightStatusList` |
| `departures()` | IIAC | `StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp`, `StatusOfPassengerFlightsDeOdp/getPassengerDeparturesDeOdp` |
| `arrivals()` | IIAC | `StatusOfPassengerFlightsOdp/getPassengerArrivalsOdp`, `StatusOfPassengerFlightsDeOdp/getPassengerArrivalsDeOdp` |
| `aircraft_assignments()` | KAC | `FlightStatusAPLList/getFlightStatusAPLList` |
| `parking_fees()` | KAC | `AirportParkingFee/parkingfee` |
| `parking_status()` | KAC | `AirportParkingCongestion/airportParkingCongestionRT` |
| `parking_status()` | IIAC | `StatusOfParking/getTrackingParking` |
| `arrival_congestion()` | IIAC | `StatusOfArrivals/getArrivalsCongestion` |
| `passenger_forecast()` | IIAC | `PassengerNoticeKR/getfPassengerNoticeIKR` |
| `airport_codes()` | KAC | `AirportCodeList/getAirportCodeList` |
| `flight_schedules()` | KAC | `FlightScheduleList/getDflightScheduleList`, `getIflightScheduleList` |
| `flight_schedules()` | IIAC | `PaxFltSched/getPaxFltSchedArrivals`, `getPaxFltSchedDepartures` |
| `airport_facilities()` | KAC | `AirportFacilities/getAirportFacilities` |
| `airport_facilities()` | IIAC | `StatusOfFacility/getFacilityKR` |
| `bus_routes()` | KAC | `AirportBusInfo/businfo` |
| `bus_routes()` | IIAC | `BusInformation/getBusInfo` |
| `taxi_status()` | KAC | `taxiWaitInfo/getJejuTaxiWaitInfo` |
| `taxi_status()` | IIAC | `StatusOfTaxi/getTaxiStatus` |
| `world_weather()` | IIAC | `StatusOfPassengerWorldWeatherInfo/getPassengerArrivalsWorldWeather`, `getPassengerDeparturesWorldWeather` |
| `service_destinations()` | IIAC | `StatusOfSrvDestinations/getServiceDestinationInfo` |

## Raw 지원 API

### KAC

KAC 서비스 목록에서 확인한 REST service는 모두 아래 형태로 접근할 수 있습니다.

```python
client.kac_raw_items("noise", "getNoise", {"pageNo": 1})
```

`service`와 `operation`은 영문/숫자/underscore만 허용합니다. 이 제한은 URL 오용을 막기 위한 것입니다.

공식 서비스 목록에서 확인한 주요 KAC service:

| Service | 상태 |
|---|---|
| `FlightStatusList` | raw |
| `FlightScheduleList` | typed |
| `AirportCodeList` | typed |
| `AirportParkingCongestion` | typed |
| `AirportParking` | typed via `KacClient.parking_status(realtime=True)` |
| `AirportParkingFee` | typed |
| `FlightStatusAPLList` | typed |
| `AirportFacilities` | typed |
| `AirportBusInfo` | typed |
| `taxiWaitInfo` | typed |
| `dailyExpectPassenger` | raw |
| `totalAirportStatsService` | raw |
| `AirportStatsService` | raw |
| airport-specific stats services | raw |
| `noise`, `noiseMeasureService` | raw |
| `airportLowVisibility`, `airportLowVisiblity` | raw |
| `contractService`, `AirportLeaseInfo` | raw |
| `ValetParking` | raw |
| `serviceLine`, `apronAirport`, `FlightApronStateList` | raw |

### IIAC

IIAC `B551177` service는 아래 형태로 접근할 수 있습니다.

```python
client.iiac_raw_items("ShtbusInfo", "getShtbusInfo", {"pageNo": 1})
```

주요 확인 API:

| Service | Endpoint | 상태 |
|---|---|---|
| `StatusOfPassengerFlightsOdp` | passenger arrivals/departures | typed |
| `StatusOfPassengerFlightsDeOdp` | detailed passenger arrivals/departures | typed |
| `StatusOfPassengerFlightsDSOdp` | weekly passenger arrivals/departures | raw |
| `PaxFltSched` | passenger flight schedule | typed |
| `StatusOfParking` | parking status | typed |
| `ParkingChargeInfo` | parking charge rules | raw |
| `StatusOfArrivals` | arrivals congestion | typed |
| `PassengerNoticeKR` | passenger forecast | typed |
| `StatusOfTaxi` | taxi status | typed |
| `BusInformation` | bus info | typed |
| `StatusOfPassengerWorldWeatherInfo` | world weather | typed |
| `StatusOfSrvDestinations` | service destinations | typed |
| `StatusOfSrvAirlines` | service airlines | raw |
| `StatusOfCargoFlights` | cargo arrivals/departures | raw |
| `StatusOfFacility` | commercial facility KR | typed |
| `FacilitiesInformation` | multilingual facilities | raw |
| `ShtbusInfo` | shuttle bus | raw |
| `AirportRailroadOperationInfo` | airport railroad | raw |
| `OutdoorAirQualityInfo` | outdoor air quality | raw |
| `FlightClosingInfoSpot` | flight closing information | raw |
| `statusOfFltacdmmlstnAirTrafficPublic` | ACDM air traffic capacity information | raw, 기관용 변경 공지 확인 필요 |
| airport statistics APIs | raw |

## 모델 미고정 영역

다음 API는 응답 스키마가 서비스별로 넓거나, 라이브러리의 핵심 사용자 흐름에서 한 단계 떨어져 있어 `raw_items`로 먼저 열어 둡니다.

- KAC 통계 API: 공항별/월별/노선별 통계 서비스
- KAC 환경/소음 API: `noise`, `noiseMeasureService`, `EpiDataService`
- KAC 임대/상업 계약 API: `contractService`, `AirportLeaseInfo`
- KAC 저시정 API: `airportLowVisibility`, `airportLowVisiblity`
- IIAC 셔틀버스/공항철도/다국어 시설 API
- IIAC 주차요금/취항 항공사/화물기 운항/옥외 대기질/Flight Closing API
- IIAC ACDM 계열 API: 2026년 공지 기준 행정/공공기관용 URL 변경 대상
- IIAC 통계성 API

typed 모델로 승격할 때는 fixture를 먼저 추가하고, 필드별 Python 타입 assertion을 함께 추가합니다.
