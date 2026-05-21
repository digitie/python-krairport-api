---
name: krairport-python-builder
description: 한국공항공사(KAC)와 인천국제공항공사(IIAC) 공개 API를 함께 다루는 `krairport` Python client를 구현, 확장, 디버깅, 문서화할 때 사용한다.
---

# Krairport Python Library Builder

`krairport`는 KAC와 IIAC 공항 공개 API를 하나의 Python client로 묶는 라이브러리다. 공개 동작을 바꾸기 전에는 `README.md`와 `krairport-api.md`를 먼저 읽는다.

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. provider field, code identifier, 명령어, URL, protocol literal처럼 보존해야 하는 값만 원문을 유지한다.

## 프로젝트 불변 조건

1. Provider 경계는 실제로 다르다. `ICN`은 IIAC, 그 외 국내 공항은 KAC가 기본이다.
2. 사용자에게는 `KrairportClient` 하나를 제공하되 KAC/IIAC HTTP와 parsing은 분리한다.
3. KAC는 XML endpoint가 많으므로 JSON을 가정하지 않는다.
4. IIAC는 대체로 `type=json`을 지원하지만 XML fallback을 유지한다.
5. data.go.kr service key는 `DATA_GO_KR_SERVICE_KEY`만 사용한다.
6. 모든 schedule timestamp는 KST로 해석한다. Windows 의존성에는 `tzdata`를 유지하고 `_time.py`의 UTC+9 fallback을 보존한다.
7. Provider mismatch를 조용히 넘기지 않는다. KAC 전용 endpoint에 `ICN`을 요청하면 `UnsupportedAirportError`를 발생시킨다.
8. 기본 test는 offline이어야 한다. 보통 test run에서 live traffic을 만들지 않는다.
9. 공개 enum은 string 호환성을 유지하기 위해 `StrEnum`을 사용한다.
10. 좌표는 WGS84 decimal degree이며 `kraddr.base.PlaceCoordinate`를 직접 쓴다. GeoJSON 순서가 필요하면 `as_geojson_position()`을 사용한다.
11. 주소는 `kraddr.base.Address`를 직접 쓴다. 공항 내부 위치 문자열은 주소 DTO와 분리한다.
12. 공개 응답 model은 Pydantic v2 기반 `KrairportModel`을 상속하고 frozen/extra forbid 설정을 유지한다.
13. 문서의 파일 경로는 `src/krairport/client.py`처럼 프로젝트 기준 상대 경로로 쓴다.
14. Python docstring과 설명 주석은 한글로 쓴다.
15. Windows에서 `rg`가 권한 문제로 막히면 PowerShell `Get-ChildItem`/`Select-String -Encoding UTF8`을 fallback으로 쓴다.
16. 이미 검증된 sibling library 구현이 있으면 불필요한 wrapper를 만들지 말고 해당 pattern을 직접 반영한다.

## 초기 지원 endpoint

| Public method | Provider | Endpoint |
|---|---|---|
| `KrairportClient.departures()` | KAC | `getDepFlightStatusList` |
| `KrairportClient.arrivals()` | KAC | `getArrFlightStatusList` |
| `KrairportClient.departures()` | IIAC | `getPassengerDeparturesDeOdp` 또는 `getPassengerDeparturesOdp` |
| `KrairportClient.arrivals()` | IIAC | `getPassengerArrivalsDeOdp` 또는 `getPassengerArrivalsOdp` |
| `KrairportClient.aircraft_assignments()` | KAC | `getFlightStatusAPLList` |
| `KrairportClient.parking_fees()` | KAC | `parkingfee` |
| `KrairportClient.parking_status()` | IIAC | `getTrackingParking` |
| `KrairportClient.arrival_congestion()` | IIAC | `getArrivalsCongestion` |
| `KrairportClient.passenger_forecast()` | IIAC | `getfPassengerNoticeIKR` |
| `KrairportClient.flight_schedules()` | KAC/IIAC | KAC `FlightScheduleList`, IIAC `PaxFltSched` |
| `KrairportClient.airport_facilities()` | KAC/IIAC | KAC `AirportFacilities`, IIAC `StatusOfFacility` |
| `KrairportClient.bus_routes()` | KAC/IIAC | KAC `AirportBusInfo`, IIAC `BusInformation` |
| `KrairportClient.taxi_status()` | KAC/IIAC | KAC `taxiWaitInfo`, IIAC `StatusOfTaxi` |
| `KrairportClient.world_weather()` | IIAC | `StatusOfPassengerWorldWeatherInfo` |
| `KrairportClient.service_destinations()` | IIAC | `StatusOfSrvDestinations` |
| `KrairportClient.kac_raw_items()` | KAC | 아직 model이 없는 KAC REST operation |
| `KrairportClient.iiac_raw_items()` | IIAC | 아직 model이 없는 B551177 REST operation |
| `KrairportClient.airport_metadata()` | local | bundled airport metadata |
| `KrairportClient.airports()` | local | provider/active filter가 적용된 airport metadata |
| `KrairportClient.nearest_airport()` | local | 가장 가까운 WGS84 공항 조회 |

Routing, parsing, model layer가 안정되기 전에는 scope를 넓히지 않는다. Coverage 판단은 `docs/api-coverage.md`를 기준으로 한다.

## 공개 API 규칙

```python
KrairportClient(
    kac_service_key=None,
    iiac_service_key=None,
    *,
    timeout=10.0,
    retries=3,
    session=None,
)

KrairportClient.from_env(
    service_key_name="DATA_GO_KR_SERVICE_KEY",
)
```

모든 공개 검색 method는 IIAC 전용 혼잡도 API가 아닌 한 명시적 `airport_code`를 받아야 한다.

### Routing

- `ICN`은 IIAC로 보낸다.
- 그 외 지원 공항은 KAC로 보낸다.
- IIAC 전용 method는 `airport_code`를 무시하지 말고 필요 시 검증한다.
- 지원하지 않는 조합은 `UnsupportedAirportError`를 발생시킨다.

### Flight model 핵심 필드

Provider별 필드명이 달라도 공개 model에는 `provider`, `airport_code`, `flight_id`, `flight_unique_id`, `direction`, `airline_name`, `airline_code`, `departure_airport_code`, `arrival_airport_code`, `scheduled_at`, `estimated_at`, `status_korean`, `status_english`, `terminal`, `gate`, `codeshare`, `raw`를 정규화해 담는다.

### 변환 정책

- 공항 코드, 항공편 번호, 고유 ID, gate/terminal 값은 문자열로 보존한다.
- schedule/estimated/changed timestamp는 KST `datetime`으로 변환한다.
- 주차 대수, 승객 수, 주차 요금, total count는 `int`로 변환한다.
- `Y`/`N` 계열 flag는 `bool | None`으로 변환한다.
- 온도, 풍속, 좌표, 비율은 `float`로 변환한다.
- 빈 문자열, 공백, `-`는 `None`으로 정규화한다.

## Provider별 요청 규칙

KAC `StatusOfFlights`, KAC `FlightStatusAPLList`, IIAC 상세 여객 항공편, IIAC 도착 혼잡도, IIAC 여객 예측 endpoint는 provider 문서의 parameter 이름을 그대로 사용한다. `airport_code`, `airport`, `schAirCode`, `f_id`, `flight_id`처럼 비슷한 이름을 임의로 합치지 않는다.

## HTTP와 parsing 규칙

1. Session/retry setup은 한 곳에 둔다.
2. Service key를 log에 남기지 않는다.
3. `429`, `500`, `502`, `503`, `504` 같은 transient error만 retry한다.
4. KAC XML parsing은 parser layer에 모으고 client method에 흩뿌리지 않는다.
5. `items.item`이 단일 dict이든 list이든 같은 내부 list 형태로 정규화한다.
6. `raw` payload는 normalization 이후 보존하며 공개 표면 자체로 삼지 않는다.

## Exception 계층

```text
KrairportError
├── KrairportAuthError
├── KrairportRequestError
├── KrairportRateLimitError
├── KrairportNetworkError
├── KrairportServerError
├── KrairportParseError
└── UnsupportedAirportError
```

Provider별 특이 동작은 이 공통 exception으로 mapping한다.

## Test 규칙

필수 offline test는 provider routing, KAC/IIAC mismatch rejection, XML/JSON 단일·다중 item normalization, timestamp parsing, Windows timezone fallback, 공개 model type assertion, code-share boolean mapping, numeric conversion, result-code/HTTP error mapping, CLI JSON serialization, Pydantic validation/frozen dump, raw endpoint path validation, enum string compatibility, `PlaceCoordinate`/`Address` 직렬화, GeoJSON coordinate order, bundled airport metadata filter, nearest airport lookup을 포함한다.

Optional live test는 `live_kac` 또는 `live_iiac` marker를 사용하고 matching env var가 없으면 skip한다. 실시간 traffic/flight count처럼 변동성이 큰 값은 assert하지 않는다.

## 흔한 실수

- `ICN`을 일반 KAC 공항처럼 처리하지 않는다.
- 모든 endpoint가 JSON을 지원한다고 가정하지 않는다.
- `airport_code`, `airport`, `schAirCode`를 혼동하지 않는다.
- `flight_id`와 `f_id`를 혼동하지 않는다.
- `2400`을 day-boundary 없이 일반 시각으로 parsing하지 않는다.
- 주차 요금과 주차 현황을 같은 schema로 보지 않는다.
- 사용자에게 `terno`, `schAPLno` 같은 provider-native 이름을 그대로 노출하지 않는다.
- coverage를 주장할 때 `docs/api-coverage.md`를 함께 갱신한다.
- local absolute path를 문서에 쓰지 않는다.
- 영어 Python docstring/설명 주석을 다시 넣지 않는다.
- blocked `rg`를 반복하지 말고 PowerShell fallback으로 전환한다.
- debug UI fixture 저장 전 민감값 redaction을 거친다.

## 문서 갱신 규칙

- 사용자 API 변경: `README.md`
- endpoint scope, parameter 차이, model 규칙: `krairport-api.md`
- fixture/live marker 정책: `docs/testing.md`
- enum/type/coordinate 정책: `docs/coordinates-and-types.md`
- 사용자에게 보이는 failure의 known fix: `docs/troubleshooting.md`
- release-facing 변경: `CHANGELOG.md`
- 반복 실수: `docs/repeated-mistakes.md`

## Debug UI fixture 규칙

Streamlit과 UI 전용 의존성은 `krairport` package 밖에 둔다. `KrairportClient.debug()` 또는 `debug_*` helper로 `DebugRun`을 만들고, 생성된 case는 `tests/fixtures/{function}/{case}.json`에 저장한다. 기본 pytest replay는 외부 API를 호출하지 않고 `tests/runners.py`를 사용한다.
