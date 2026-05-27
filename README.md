# python-krairport-api

## Debug UI와 fixture replay

`krairport`는 디버그 UI가 테스트 fixture를 만들 수 있도록 `DebugRun`과
`KrairportClient.debug()`를 제공합니다. 라이브러리 자체는 Streamlit에 의존하지 않고,
`tools/streamlit_debug_ui`의 별도 UI 패키지가 설치된 `krairport`를 import해서 실행합니다.

```python
from krairport import KrairportClient

client = KrairportClient.from_env()
run = client.debug_departures(airport_code="GMP", searchday="20260430")
print(run.response["body"])
print(run.processed)
```

저장된 fixture는 `tests/fixtures/{function}/{case}.json`에 두며,
`python -m pytest tests/test_generated_fixtures.py`가 외부 API 호출 없이 replay합니다.
자세한 설계와 assertion mode는 [docs/debug-fixtures.md](docs/debug-fixtures.md)를 참고하세요.

지원 endpoint 카탈로그는 `api_catalog()`로 확인할 수 있습니다. 각 항목에는 사람이 읽는
데이터셋명과 공공데이터포털 서비스키 신청 링크가 포함됩니다.

```python
from krairport import api_catalog

for item in api_catalog("departures"):
    print(item.provider, item.dataset_name, item.service_key_url)
```

## Async/httpx client shape

The runtime transport is httpx-based. The synchronous facade remains compatible
with existing callers, and the async facade follows the `python-krheritage-api`
style:

```python
from krairport import AsyncKrairportClient, KrairportClient

with KrairportClient.from_env() as client:
    rows = client.departures(airport_code="GMP", num_of_rows=10)

async with AsyncKrairportClient.from_env() as client:
    rows = await client.world_weather(direction="arrival", airport_code="ICN")
```

For `python-krtour-map` integration, public provider models keep `raw`, expose
Pydantic `model_dump(mode="json")`, and the client exposes `iter_pages(...)`
with the common `page_no` / `num_of_rows` contract:

```python
client = KrairportClient.from_env()
for page in client.iter_pages(
    client.world_weather,
    direction="arrival",
    airport_code="ICN",
    num_of_rows=100,
    max_pages=2,
):
    print(page.page, len(page.items))
```

한국공항공사(KAC)와 인천국제공항공사(IIAC) OpenAPI를 하나의 Python 인터페이스로 묶기 위한 공항 데이터 라이브러리 설계 문서입니다.

`python-krairport-api`는 "인천공항은 인천국제공항공사, 그 외 전국공항은 한국공항공사"라는 공급자 경계를 내부에서 흡수하고, 운항/주차/혼잡도/공항 메타데이터를 Pydantic 기반 Python 타입 모델로 일관되게 제공하는 것을 목표로 합니다. Python 코드에서는 `krairport`로 import합니다.

> 현재 저장소는 `0.1.0` 초기 구현을 포함합니다. KAC/IIAC provider adapter, 통합 `KrairportClient`, KST 시간 파서, XML/JSON 정규화, CLI, fixture 기반 테스트가 들어 있으며, live API 테스트는 서비스키가 있을 때 별도 marker로 확장합니다.

---

## 핵심 특징

- **KAC + IIAC 통합 인터페이스**: 사용자는 공항코드만 넘기고, 라이브러리가 적절한 공급자 API를 선택합니다.
- **공항 라우팅 내장**: `ICN`은 IIAC, 그 외 KAC 운영 공항은 KAC API로 자동 분기합니다.
- **운항/주차/교통/시설 중심 초기 범위**: 항공편 도착/출발, 정기 운항스케줄, 항공기 등록번호/기종, 주차요금/현황, 입국장 혼잡도, 승객예고, 공항버스/택시, 시설/취항지/기상을 우선 지원 대상으로 둡니다.
- **JSON/XML 차이 흡수**: KAC의 XML 중심 응답과 IIAC의 JSON/XML 응답을 내부에서 정규화합니다.
- **KST datetime 표준화**: `YYYYMMDD`, `HHMM`, `YYYYMMDDHHMM`, 과학적 표기 숫자 문자열 등을 timezone-aware `datetime`이나 `int`/`str`로 변환합니다.
- **공급자별 필드명 흡수**: `airport_code`, `schAirCode`, `airport`, `flight_id`, `f_id`, `schFID`처럼 기관마다 다른 필드명을 Pythonic 인터페이스로 통합합니다.
- **Pydantic 모델**: `Flight`, `AircraftAssignment`, `ParkingFee`, `ArrivalCongestion`, `PassengerForecast` 같은 immutable `BaseModel`과 public `StrEnum`/type alias를 제공합니다.
- **위경도 표준화**: 공항 좌표와 provider 좌표 필드를 `krairport.Coordinate`로 정규화하고, GeoJSON용 `(longitude, latitude)` 변환을 제공합니다.
- **주소 표준화**: 시설 provider row의 주소 필드는 문자열로 보존하고, 공항 내부 위치 문자열은 `location`에 따로 보존합니다.
- **공항 메타데이터 레지스트리**: `get_airport()`, `list_airports()`, `nearest_airport()`로 지도/검색/근접 공항 계산을 지원합니다.
- **누락 API raw fallback**: 아직 typed 모델로 고정하지 않은 KAC/IIAC 공식 엔드포인트도 `kac_raw_items()` / `iiac_raw_items()`로 접근할 수 있습니다.
- **fixture 기반 테스트 우선**: 기본 테스트는 실 API 호출 없이 동작하고, live 테스트는 각 기관 서비스키가 있을 때만 분리 실행합니다.

---

## 시작하기

### 1단계: 인증키 발급

KAC/IIAC 모두 data.go.kr 계열 서비스이므로 환경변수 이름은 하나로 통일합니다.

1. [공공데이터포털](https://www.data.go.kr)에서 한국공항공사 API 활용신청을 합니다.
2. 같은 포털에서 인천국제공항공사 API 활용신청을 합니다.
3. 발급받은 디코딩 인증키를 환경변수로 저장합니다.

```bash
export DATA_GO_KR_SERVICE_KEY="발급받은_data.go.kr_디코딩_인증키"
```

Windows PowerShell:

```powershell
$env:DATA_GO_KR_SERVICE_KEY="발급받은_data.go.kr_디코딩_인증키"
```

### 2단계: 설치

현재는 문서/스캐폴딩 단계이므로 개발 설치를 기준으로 안내합니다.

```bash
git clone https://github.com/digitie/python-krairport-api.git
cd python-krairport-api
python -m venv .venv
pip install -e ".[dev]"
```

### 3단계: 사용 예시

```python
from krairport import Airport, Coordinate, Direction, KrairportClient

airport = KrairportClient.from_env()

# 1) 김포공항 출발편 조회 -> KAC로 자동 라우팅
for flight in airport.departures(airport_code=Airport.GMP, searchday="20260430", from_time="0600", to_time="1200"):
    print(flight.flight_id, flight.status_korean, flight.scheduled_at, flight.provider)

# 2) 인천공항 도착편 조회 -> IIAC로 자동 라우팅
for flight in airport.arrivals(airport_code="ICN", searchday="20260430", from_time="0600", to_time="1200"):
    print(flight.flight_id, flight.arrival_airport_code, flight.estimated_at, flight.terminal)

# 3) 인천공항 입국장 혼잡도
for row in airport.arrival_congestion(terminal="T1"):
    print(row.entry_gate, row.flight_id, row.korean_count, row.foreign_count)

# 4) 김포공항 주차요금
for fee in airport.parking_fees(airport_code="GMP"):
    print(fee.airport_code, fee.small_basic_minutes, fee.small_basic_fee)

# 5) 김포/제주 등 KAC 실시간 항공기 등록번호/기종
for plane in airport.aircraft_assignments(airport_code="CJU", sch_st_time="202604300600", sch_ed_time="202604301200"):
    print(plane.flight_id, plane.aircraft_registration, plane.aircraft_type)

# 6) enum/type/좌표 메타데이터 활용
icn = airport.airport_metadata(Airport.ICN)
print(icn.coordinate.as_geojson_position())
print(airport.nearest_airport(Coordinate.from_values("37.56 N", "126.79 E")).code)

# direction도 문자열과 enum을 모두 받습니다.
airport.flight_schedules(airport_code=Airport.ICN, direction=Direction.ARRIVAL)
```

---

## 제공 API

`0.1.0` 초기 구현 범위는 아래와 같습니다.

| Public method | Provider | Source endpoint | 반환 |
|---|---|---|---|
| `KrairportClient.departures(...)` | KAC 또는 IIAC | KAC `getDepFlightStatusList`, IIAC `getPassengerDeparturesDeOdp`/`getPassengerDeparturesOdp` | `list[Flight]` |
| `KrairportClient.arrivals(...)` | KAC 또는 IIAC | KAC `getArrFlightStatusList`, IIAC `getPassengerArrivalsDeOdp`/`getPassengerArrivalsOdp` | `list[Flight]` |
| `KrairportClient.aircraft_assignments(...)` | KAC | `getFlightStatusAPLList` | `list[AircraftAssignment]` |
| `KrairportClient.parking_fees(...)` | KAC | `parkingfee` | `list[ParkingFee]` |
| `KrairportClient.parking_status(...)` | KAC 또는 IIAC | KAC `airportParkingCongestionRT`, IIAC `getTrackingParking` | `list[ParkingAreaStatus]` |
| `KrairportClient.arrival_congestion(...)` | IIAC | `getArrivalsCongestion` | `list[ArrivalCongestion]` |
| `KrairportClient.passenger_forecast(...)` | IIAC | `getfPassengerNoticeIKR` | `list[PassengerForecast]` |
| `KrairportClient.flight_schedules(...)` | KAC 또는 IIAC | KAC `getDflightScheduleList`/`getIflightScheduleList`, IIAC `getPaxFltSchedArrivals`/`getPaxFltSchedDepartures` | `list[FlightSchedule]` |
| `KrairportClient.airport_facilities(...)` | KAC 또는 IIAC | KAC `getAirportFacilities`, IIAC `getFacilityKR` | `list[AirportFacility]` |
| `KrairportClient.bus_routes(...)` | KAC 또는 IIAC | KAC `businfo`, IIAC `getBusInfo` | `list[BusRoute]` |
| `KrairportClient.taxi_status(...)` | KAC 또는 IIAC | KAC `getJejuTaxiWaitInfo`, IIAC `getTaxiStatus` | `list[TaxiStatus]` |
| `KrairportClient.world_weather(...)` | IIAC | `getPassengerArrivalsWorldWeather`/`getPassengerDeparturesWorldWeather` | `list[WorldWeather]` |
| `KrairportClient.service_destinations(...)` | IIAC | `getServiceDestinationInfo` | `list[ServiceDestination]` |
| `KrairportClient.kac_raw_items(...)` | KAC | 임의 KAC service/operation | `list[dict]` |
| `KrairportClient.iiac_raw_items(...)` | IIAC | 임의 B551177 service/operation | `list[dict]` |
| `KrairportClient.airport_metadata(...)` | local | 번들 공항 메타데이터 | `AirportMetadata` |
| `KrairportClient.airports(...)` | local | provider/active 필터 가능한 메타데이터 목록 | `tuple[AirportMetadata, ...]` |
| `KrairportClient.nearest_airport(...)` | local | WGS84 좌표 기준 근접 공항 | `AirportMetadata | None` |

자세한 커버리지와 raw 지원 범위는 [docs/api-coverage.md](docs/api-coverage.md), enum/type/좌표 규칙은 [docs/coordinates-and-types.md](docs/coordinates-and-types.md)를 참고하세요.

확장 권장 순서:

1. `departures()` / `arrivals()`로 공항 라우팅 계층 완성
2. `aircraft_assignments()`로 KAC 운항 부가정보 연동
3. `parking_fees()` / `parking_status()`로 주차 계열 분리
4. `arrival_congestion()` / `passenger_forecast()`로 IIAC 혼잡도 계열 추가
5. `kac_raw_items()` / `iiac_raw_items()`로 아직 typed 모델이 없는 공식 엔드포인트를 먼저 연결한 뒤 fixture가 쌓이면 모델 승격

---

## 응답 모델

### `Flight`

```python
from datetime import datetime
from krairport import Direction, KrairportModel, Provider

class Flight(KrairportModel):
    provider: Provider
    airport_code: str
    flight_id: str
    flight_unique_id: str | None
    direction: Direction
    airline_name: str | None
    airline_code: str | None
    departure_airport_code: str | None
    arrival_airport_code: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    status_korean: str | None
    status_english: str | None
    terminal: str | None
    gate: str | None
    codeshare: bool | None
    raw: dict
```

### `AircraftAssignment`

```python
class AircraftAssignment(KrairportModel):
    airport_code: str
    flight_id: str
    flight_unique_id: str | None
    aircraft_registration: str | None
    aircraft_type: str | None
    airline_name: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    gate: str | None
    raw: dict
```

### `ParkingFee`

```python
class ParkingFee(KrairportModel):
    airport_code: str
    parking_name: str | None
    small_basic_minutes: int | None
    small_basic_fee: int | None
    large_basic_minutes: int | None
    large_basic_fee: int | None
    small_daily_max_fee: int | None
    large_daily_max_fee: int | None
    raw: dict
```

### `ArrivalCongestion`

```python
class ArrivalCongestion(KrairportModel):
    terminal: str
    entry_gate: str
    flight_id: str | None
    airport_code: str | None
    gate_number: str | None
    scheduled_at: datetime | None
    estimated_at: datetime | None
    korean_count: int | None
    foreign_count: int | None
    raw: dict
```

### `PassengerForecast`

```python
class PassengerForecast(KrairportModel):
    display_date: str
    time_range: str
    t1_arrival_east: int | None
    t1_arrival_west: int | None
    t1_departure_total: int | None
    t2_arrival_total: int | None
    t2_departure_total: int | None
    raw: dict
```

---

## Python 타입 정책

공항 OpenAPI는 기관마다 응답형식과 필드명이 크게 다르지만, `krairport`는 모델 경계에서 타입을 정규화하는 것을 기본 원칙으로 둡니다.

| 원본 값 | Python 표면 타입 | 규칙 |
|---|---|---|
| `20260430` | `date` 또는 `str` | 날짜 의미가 확실하면 `date`, 단순 조회 키면 `str` 유지 |
| `0600`, `2400` | `str` | 조회 파라미터는 zero-padding 보존 |
| `202604300930` | KST aware `datetime` | 일정/변경 시각은 `Asia/Seoul` 기준 |
| `2.02112E+11` | `datetime` 또는 정규화된 문자열 | IIAC 과학적 표기 시각은 안전하게 파싱 |
| `Y` / `N` | `bool` | 코드쉐어/사용여부 계열 |
| 숫자형 문자열 | `int` 또는 `float` | 의미가 count/요금이면 `int`, 비율/소수면 `float` |
| 공항코드 `GMP`, `ICN` | `str` 또는 `Airport` | 항상 대문자 IATA 코드 보존 |
| 공급자/방향 | `Provider`, `Direction` | `StrEnum`이라 문자열 비교/JSON 직렬화 가능 |
| 위경도 | `Coordinate` | WGS84 decimal degrees, public DTO `(lat, lon)`, GeoJSON은 `as_geojson_position()` |
| 주소 | `str | None` | provider 주소 필드는 문자열로 보존, 내부 위치는 `location` |
| 편명 `KE123`, `7C1101` | `str` | leading zero 가능성을 고려해 숫자형 변환 금지 |
| 빈 문자열, 공백 | `None` | 공통 정규화 |

모든 public 응답 모델은 Pydantic v2 `BaseModel` 기반입니다. 외부 앱에서는 `model_dump(mode="json")`, `model_dump_json()`, 또는 `to_dict()` / `to_json()`을 사용할 수 있습니다.

---

## 공급자 라우팅 규칙

한국 공항 OpenAPI는 **기관별 책임 경계**가 분명합니다.

| 공항 | 공급자 | 비고 |
|---|---|---|
| `ICN` | 인천국제공항공사 (IIAC) | 인천공항 전용 |
| `GMP`, `PUS`, `CJU`, `TAE`, `CJJ`, `KWJ`, `RSU`, `USN`, `MWX`, `YNY`, `KUV`, `HIN`, `WJU`, `KPO` 등 | 한국공항공사 (KAC) | 인천 제외 전국공항 |

핵심 규칙:

- `ICN` 관련 운항/주차/혼잡도는 **무조건 IIAC**로 보냅니다.
- KAC 데이터셋 설명에 "전국공항(인천공항 제외)"가 명시된 경우 `ICN` 요청을 허용하지 않습니다.
- IIAC의 입국장/승객예고/주차 데이터는 인천공항 전용이므로 다른 공항코드로 우회하지 않습니다.
- 통합 클라이언트는 `airport_code`만 보고 provider를 선택하되, low-level provider client도 별도로 둡니다.

---

## 에러 처리

```text
KrairportError
├── KrairportAuthError         # 인증키 오류, 활용승인 미완료
├── KrairportRequestError      # 잘못된 파라미터, 지원하지 않는 공항/조합
├── KrairportRateLimitError    # 일 트래픽 초과
├── KrairportNetworkError      # httpx timeout / connection error
├── KrairportServerError       # 5xx, 공급자 응답 이상
├── KrairportParseError        # XML/JSON 구조 또는 타입 변환 오류
└── UnsupportedAirportError    # 해당 기능을 지원하지 않는 공항
```

기관별 에러 코드/메시지는 다르므로 내부에서 매핑하되, public API는 위 공통 예외 계층만 노출하는 쪽을 권장합니다.

---

## 개발

```bash
python -m compileall src/krairport tests
python -m pytest
python -m pytest --cov=krairport --cov-fail-under=85
ruff check .
mypy src/krairport
```

기본 테스트는 실 API를 호출하지 않는 fixture 기반이어야 합니다. 실제 키를 사용하는 테스트는 아래처럼 분리합니다.

```bash
pytest -m live_kac
pytest -m live_iiac
```

자세한 테스트 정책은 [docs/testing.md](docs/testing.md), 반복 실수 방지 로그는 [docs/repeated-mistakes.md](docs/repeated-mistakes.md), 장애 대응 메모는 [docs/troubleshooting.md](docs/troubleshooting.md)를 참고하세요.

---

## 프로젝트 파일

```text
.
├── README.md
├── AGENTS.md
├── krairport-api.md
├── SKILL.md
├── CHANGELOG.md
├── pyproject.toml
├── docs/
│   ├── repeated-mistakes.md
│   ├── coordinates-and-types.md
│   ├── testing.md
│   └── troubleshooting.md
├── src/
│   └── krairport/
│       ├── __init__.py
│       ├── airports.py
│       ├── client.py
│       ├── providers/
│       │   ├── kac.py
│       │   └── iiac.py
│       ├── models.py
│       ├── enums.py
│       ├── types.py
│       ├── exceptions.py
│       ├── _http.py
│       ├── _xml.py
│       ├── _time.py
│       ├── _convert.py
│       ├── _routing.py
│       ├── cli.py
│       └── py.typed
```

테스트 구조:

```text
tests/
├── fixtures/
├── test_airports.py
├── test_client.py
├── test_cli.py
├── test_convert.py
├── test_geo.py
├── test_http.py
├── test_kac.py
├── test_iiac.py
├── test_pydantic_models.py
├── test_routing.py
├── test_time.py
└── test_xml.py
```

---

## 운영상 주의

- KAC와 IIAC는 **같은 공항 데이터처럼 보여도 파라미터명과 시간 의미가 다릅니다**.
- KAC는 XML-only 엔드포인트가 아직 많으므로 JSON 가정 금지입니다.
- IIAC는 동일한 주제에 `당일 Odp`, `상세 DeOdp`, `혼잡도`, `승객예고`처럼 API가 나뉘므로 이름이 비슷해도 응답 스키마가 다릅니다.
- IIAC 공공데이터포털 서비스는 2026년에도 URL 변경 공지가 있었으므로, 새 API를 typed 모델로 올리기 전 `docs/api-coverage.md`와 변경 공지를 먼저 확인합니다.
- 상세 운항 API는 KAC/IIAC 모두 `D-3 ~ D+6` 범위 문서가 많지만, 당일 운항 API는 `당일` 또는 `H-2 ~ H+2` 같은 더 좁은 범위를 사용합니다.
- 일부 IIAC 응답 예시에는 `estimatedtime`, `scheduletime`이 일반 문자열이 아니라 과학적 표기처럼 보이는 예시가 있어 파서가 느슨해야 합니다.
- 좌표는 `krairport.Coordinate`를 사용합니다. `as_tuple()`과 `as_lat_lon()`은 `(latitude, longitude)`이고, GeoJSON 순서가 필요하면 `as_geojson_position()`을 사용합니다.
- 문서의 파일 위치 정보는 `src/krairport/client.py`처럼 프로젝트 기준 상대 경로로 작성합니다.
- Python 내부 문서(module/class/function docstring과 설명용 주석)는 한글로 작성합니다. provider 원문, 코드 식별자, URL은 원문을 유지합니다.
- Windows 작업 환경에서 `rg`가 권한 문제로 막히면 PowerShell `Get-ChildItem` / `Select-String`으로 우회합니다.
- PowerShell에서 한글 문서를 읽거나 검색할 때는 `Get-Content -Encoding UTF8`, `Select-String -Encoding UTF8`처럼 인코딩을 명시합니다.
- 문서상 `serviceURL`과 실제 요청 함수명이 분리되므로 base URL + operation 경로를 함께 관리해야 합니다.
- Windows/Python 환경에는 IANA timezone database가 없을 수 있으므로 `tzdata` 의존성을 포함합니다. 설치 전 실행 환경에서도 `Asia/Seoul` 고정 UTC+9 fallback을 사용합니다.

---

## 참고 링크

확인 기준일: **2026-05-06**

- [한국공항공사 실시간 항공운항 현황 상세 조회 서비스](https://www.data.go.kr/data/15113771/openapi.do)
- [한국공항공사 전국공항 실시간 항공기 기종 및 등록번호 정보](https://www.data.go.kr/data/15144867/openapi.do)
- [한국공항공사 전국공항 주차요금](https://www.data.go.kr/data/15038474/openapi.do)
- [한국공항공사 오픈 API 서비스 목록](https://openapi.airport.co.kr/service)
- [인천국제공항공사 여객기 운항 현황 상세 조회 서비스](https://www.data.go.kr/data/15112968/openapi.do)
- [인천국제공항공사 여객편 운항현황(다국어)](https://www.data.go.kr/data/15095093/openapi.do)
- [인천국제공항공사 주차 정보](https://www.data.go.kr/data/15095047/openapi.do)
- [OurAirports data downloads](https://ourairports.com/data/)
- [인천국제공항공사 입국장현황 정보 서비스](https://www.data.go.kr/data/15095061/openapi.do)
- [인천국제공항공사 승객예고-출·입국장별](https://www.data.go.kr/data/15095066/openapi.do)

---

## 변경 이력

- `0.1.0`: KAC/IIAC 통합 클라이언트, provider adapter, KST 시간/타입 변환, XML/JSON 파서, CLI, fixture 기반 테스트와 문서 보강.
