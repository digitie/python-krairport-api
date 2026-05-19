# krairport API 명세

## DebugRun / fixture 생성 API

디버그 UI와 fixture replay를 위해 `src/krairport/debug.py`를 public 보조 API로 둡니다.

```python
from krairport import DebugRun, KrairportClient

client = KrairportClient.from_env()
run: DebugRun = client.debug("departures", airport_code="GMP", searchday="20260430")
```

지원 함수 이름은 `departures`, `arrivals`, `aircraft_assignments`, `parking_fees`,
`parking_status`, `arrival_congestion`, `passenger_forecast`, `airport_codes`,
`flight_schedules`, `airport_facilities`, `bus_routes`, `taxi_status`,
`world_weather`, `service_destinations`, `kac_raw_items`, `iiac_raw_items`입니다.

`DebugRun`은 `input`, `request`, `response`, `parsed`, `processed`, `trace`, `error`를
분리합니다. fixture 저장 시 `serviceKey`, `Authorization`, `api_key`,
access/refresh token 계열 값은 `<REDACTED>`로 마스킹합니다.

`tests/test_generated_fixtures.py`는 `tests/fixtures/*/*.json`을 읽어 외부 API 호출 없이
replay 테스트를 수행합니다. 자세한 포맷은 `docs/debug-fixtures.md`를 기준으로 합니다.

`api_catalog(function_name=None, provider=None)`는 지원 API 카탈로그를 반환합니다.
카탈로그 항목에는 `dataset_name`과 `service_key_url`이 포함되어 UI에서 데이터셋명을
사람이 읽기 쉬운 이름으로 표시하고 공공데이터포털 활용신청 페이지를 연결할 수 있습니다.

`krairport`는 한국공항공사(KAC)와 인천국제공항공사(IIAC) OpenAPI를 통합하는 Python 라이브러리입니다. 이 문서는 `0.1.0` 구현과 이후 확장의 public API, 공급자 라우팅, 타입 변환, 테스트 기준을 고정하기 위한 명세입니다.

## 1. 범위

`0.1.0` 범위는 다음 도메인을 포함합니다.

1. 운항 조회
2. 주차 정보
3. 인천공항 혼잡도/승객예고
4. 공항 교통/시설/취항지/기상
5. 외부 프로그램용 enum/type/좌표/공항 메타데이터

초기 지원 엔드포인트:

| Domain | Provider | Operation | 비고 |
|---|---|---|---|
| 항공편 출발 | KAC | `getDepFlightStatusList` | 전국공항(인천 제외) |
| 항공편 도착 | KAC | `getArrFlightStatusList` | 전국공항(인천 제외) |
| 항공기 기종/등록번호 | KAC | `getFlightStatusAPLList` | KAC 운항조회 보강용 |
| 주차요금 | KAC | `parkingfee` | XML-only |
| 여객편 당일 도착 | IIAC | `getPassengerArrivalsOdp` | 당일 운항 |
| 여객편 당일 출발 | IIAC | `getPassengerDeparturesOdp` | 당일 운항 |
| 여객편 상세 도착 | IIAC | `getPassengerArrivalsDeOdp` | D-3 ~ D+6 |
| 여객편 상세 출발 | IIAC | `getPassengerDeparturesDeOdp` | D-3 ~ D+6 |
| 주차현황 | IIAC | `getTrackingParking` | T1/T2 주차장별 |
| 입국장 혼잡도 | IIAC | `getArrivalsCongestion` | 현재시간 기준 -2h ~ +2h |
| 승객예고 | IIAC | `getfPassengerNoticeIKR` | 조회일과 다음날 |
| 공항코드 | KAC | `getAirportCodeList` | 전국공항 코드 |
| 정기운항 스케줄 | KAC/IIAC | KAC `FlightScheduleList`, IIAC `PaxFltSched` | 국내/국제, 도착/출발 |
| 공항시설/상업시설 | KAC/IIAC | KAC `AirportFacilities`, IIAC `StatusOfFacility` | 시설명/층/위치/주소 |
| 버스 | KAC/IIAC | KAC `AirportBusInfo`, IIAC `BusInformation` | 노선/요금/승차장 |
| 택시 | KAC/IIAC | KAC `taxiWaitInfo`, IIAC `StatusOfTaxi` | 제주 택시대기, 인천 택시출차 |
| 세계날씨 | IIAC | `StatusOfPassengerWorldWeatherInfo` | 상대 공항 기상 |
| 취항도시 | IIAC | `StatusOfSrvDestinations` | 도시/공항 코드 |

## 2. 공급자 불변조건

### 2.1 한국공항공사 (KAC)

- Base service list: `https://openapi.airport.co.kr/service`
- 주요 REST base:
  - `https://openapi.airport.co.kr/service/rest/StatusOfFlights`
  - `https://openapi.airport.co.kr/service/rest/FlightStatusAPLList`
  - `https://openapi.airport.co.kr/service/rest/AirportParkingFee`
- 인증 파라미터: `serviceKey`
- 응답 형식:
  - 운항 현황: XML + 일부 JSON 문서화
  - 항공기 기종/등록번호: XML
  - 주차요금: XML
- 공항 범위: **인천공항 제외**

### 2.2 인천국제공항공사 (IIAC)

- Base service family: `https://apis.data.go.kr/B551177/...`
- 인증 파라미터: `serviceKey`
- 응답 형식: JSON + XML
- 공항 범위: **인천공항 전용**
- 추가 공통 파라미터: `type=json|xml`

### 2.3 라우팅 규칙

- `ICN` 요청은 IIAC만 허용
- `ICN` 이외 공항의 운항/주차요금 요청은 KAC 우선
- `parking_status`는 `ICN`이면 IIAC, 그 외 KAC 공항이면 KAC
- `arrival_congestion`, `passenger_forecast`는 IIAC 전용
- 잘못된 기관-공항 조합은 `UnsupportedAirportError`

## 3. Public API 설계

### 3.1 상위 클라이언트

```python
KrairportClient(
    kac_service_key: str | None = None,
    iiac_service_key: str | None = None,
    *,
    timeout: float = 10.0,
    retries: int = 3,
    session: httpx.Client-compatible object | None = None,
)

KrairportClient.from_env(
    kac_name: str = "KAC_SERVICE_KEY",
    iiac_name: str = "IIAC_SERVICE_KEY",
    env_file: str | None = None,
)

AsyncKrairportClient.from_env(...)
KrairportClient.aio(...)
```

상위 클라이언트는 `python-krheritage-api`와 같은 형태로 context manager와 async facade를 제공합니다.
동기 facade는 기존 호출을 유지하고, 비동기 facade는 `httpx.AsyncClient` 기반 provider client를 사용합니다.

```python
from krairport import AsyncKrairportClient, KrairportClient

with KrairportClient.from_env() as client:
    rows = client.departures(airport_code="GMP")

async with AsyncKrairportClient.from_env() as client:
    rows = await client.world_weather(direction="arrival", airport_code="ICN")
```

`from_env()`는 process env를 먼저 보고, 없으면 현재 작업 디렉터리와 상위 디렉터리의
`.env` / `.env.local`에서 `KAC_SERVICE_KEY`, `IIAC_SERVICE_KEY`, `DATA_GO_KR_SERVICE_KEY`,
`DATA_GOKR_SERVICE_KEY`, `PUBLIC_DATA_SERVICE_KEY`를 찾습니다. 복사/붙여넣기 과정에서 들어간
앞뒤 공백과 따옴표는 서비스키로 사용하기 전에 제거합니다.

`python-krtour-map` 호환성 기준:

- provider public client를 직접 호출할 수 있어야 하며 별도 wrapper/adapter를 요구하지 않습니다.
- 모든 typed response model은 `raw`를 보존하거나 `model_dump(mode="json")`으로 원문 추적이 가능해야 합니다.
- page 기반 수집은 `iter_pages(fetch_page, page_no=..., num_of_rows=..., max_pages=...)`를 사용합니다.
- `PROVIDER_NAME == "python-krairport-api"`를 canonical provider name으로 노출합니다.

### 3.2 운항

```python
def departures(
    self,
    *,
    airport_code: str,
    searchday: str | None = None,
    from_time: str | None = None,
    to_time: str | None = None,
    flight_id: str | None = None,
    flight_unique_id: str | None = None,
    airline_code: str | None = None,
    line: str | None = None,
    lang: str = "K",
    use_detailed: bool | None = None,
    page_no: int = 1,
    num_of_rows: int = 10,
) -> list[Flight]: ...

def arrivals(...same shape...) -> list[Flight]: ...
```

정책:

- `airport_code="ICN"`이면 IIAC
- `airport_code!="ICN"`이면 KAC
- `use_detailed`:
  - `True`: IIAC는 `DeOdp`
  - `False`: IIAC는 당일 `Odp`
  - `None`: `searchday`가 오늘이면 `Odp`, 그 외 `DeOdp`

### 3.3 KAC 항공기 기종/등록번호

```python
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
) -> list[AircraftAssignment]: ...
```

### 3.4 주차

```python
def parking_fees(
    self,
    *,
    airport_code: str | None = None,
) -> list[ParkingFee]: ...

def parking_status(
    self,
    *,
    airport_code: str = "ICN",
    page_no: int = 1,
    num_of_rows: int = 100,
) -> list[ParkingAreaStatus]: ...
```

### 3.5 혼잡도 / 승객예고

```python
def arrival_congestion(
    self,
    *,
    terminal: str | None = None,   # T1, T2
    airport: str | None = None,    # 출발지 공항 IATA
    page_no: int = 1,
    num_of_rows: int = 100,
) -> list[ArrivalCongestion]: ...

def passenger_forecast(
    self,
    *,
    selectdate: int = 0,  # 0=today, 1=tomorrow
    page_no: int = 1,
    num_of_rows: int = 100,
) -> list[PassengerForecast]: ...
```

### 3.6 공항 메타데이터 / 좌표

```python
def airport_metadata(self, airport_code: str) -> AirportMetadata: ...

def airports(
    self,
    *,
    provider: ProviderLike | None = None,
    active: bool | None = None,
) -> tuple[AirportMetadata, ...]: ...

def nearest_airport(
    self,
    coordinate: PlaceCoordinate,
    *,
    provider: ProviderLike | None = None,
    active: bool | None = True,
) -> AirportMetadata | None: ...
```

정책:

- 번들 좌표는 WGS84 decimal degrees를 표준으로 둡니다.
- 좌표 public surface는 `kraddr.base.PlaceCoordinate`를 직접 사용합니다.
- `PlaceCoordinate.as_tuple()`은 public DTO 순서인 `(latitude, longitude)`이고, `PlaceCoordinate.as_geojson_position()`은 GeoJSON 표준인 `(longitude, latitude)`입니다.
- UI나 사람이 읽는 순서는 `PlaceCoordinate.as_lat_lon()`으로 `(latitude, longitude)`를 명시합니다.
- `Airport`, `Provider`, `Direction`은 모두 `StrEnum`이므로 문자열 비교와 JSON 직렬화가 가능합니다.
- 타입 alias는 `krairport.types`에서 public API로 제공합니다.

### 3.7 누락/확장 API raw access

typed 모델로 고정하지 않은 공식 엔드포인트는 다음으로 접근합니다.

```python
client.kac_raw_items("noise", "getNoise", {"pageNo": 1})
client.iiac_raw_items("ShtbusInfo", "getShtbusInfo", {"pageNo": 1})
```

`service`와 `operation`은 영문/숫자/underscore만 허용합니다.

## 4. 모델 규칙

모든 public 모델은:

- Pydantic v2 `BaseModel` 기반의 `KrairportModel` 상속
- `ConfigDict(frozen=True, extra="forbid")`
- 공급자 원본 스키마를 그대로 흘리지 않음
- 디버깅용 `raw: RawRecord`는 유지하되 기본값은 빈 mapping
- provider/direction은 public 표면에서 `Provider`, `Direction` enum 사용
- 좌표는 `kraddr.base.PlaceCoordinate | None`으로 표준화
- 주소는 `kraddr.base.Address | None`으로 표준화하고 `Address.from_mapping()`을 직접 사용
- JSON 직렬화는 `model_dump(mode="json")`, `model_dump_json()`, `to_dict()`, `to_json()` 사용

필수 모델:

```text
Flight
AircraftAssignment
ParkingFee
ParkingAreaStatus
ArrivalCongestion
PassengerForecast
AirportCode
AirportMetadata
Address
PlaceCoordinate
KrairportModel
```

## 5. 타입 변환 규칙

### 5.1 날짜/시간

- `searchday`: 조회 파라미터이므로 `str` 유지 (`YYYYMMDD`)
- `from_time`, `to_time`: 조회 파라미터이므로 `str` 유지 (`HHMM`)
- 일정/변경 시각:
  - `YYYYMMDDHHMM`
  - `YYYYMMDDHHMMSS`
  - 과학적 표기 문자열 (`2.02112E+11`)
  를 모두 파싱해 `Asia/Seoul` timezone-aware `datetime`으로 변환

### 5.2 숫자

- 승객수, 요금, 총면수, 주차대수: `int`
- 비율/거리/기온/풍속/소수값이 있는 경우만 `float`
- 빈 문자열, 공백, `-`: `None`

### 5.3 Enum / type alias

- `Provider`: `kac`, `iiac`
- `Direction`: `arrival`, `departure`
- `Airport`: 지원 IATA 공항코드
- `AirportCodeLike`: `str | Airport`
- `ProviderLike`: `str | Provider`
- `DirectionLike`: `str | Direction`

모든 enum은 `StrEnum`으로 구현해 기존 문자열 기반 코드와 호환합니다.

### 5.4 좌표

- 내부 표준: WGS84 decimal degrees
- public 좌표 타입: `kraddr.base.PlaceCoordinate`
- 저장/거리계산/GeoJSON 순서: `(longitude, latitude)`
- UI용 위도 우선 순서: `as_lat_lon()`의 `(latitude, longitude)`
- DMS 문자열과 `N/E/S/W` hemisphere는 decimal degrees로 변환
- 범위 밖 위도/경도는 `ValueError`

### 5.5 주소

- public 주소 타입: `kraddr.base.Address`
- provider row 주소 필드는 `Address.from_mapping()`으로 직접 변환
- 공항 내부 위치 문자열은 주소로 추정하지 않고 `AirportFacility.location`에 유지
- 자유 주소 문자열만으로 법정동코드를 임의 추정하지 않음

### 5.6 문자열 유지 규칙

다음 값은 절대 `int`로 바꾸지 않습니다.

- 공항코드 `ICN`, `GMP`
- 편명 `7C1101`
- 편명 UNIQ 코드 `2023032800000004944564`
- 터미널 `T1`, `T2`
- 입국장 게이트 `A`, `B`, `C`, `D`, `E`, `F`

## 6. 공급자별 파라미터 차이

### 6.1 KAC 운항

KAC `StatusOfFlights` WADL 기준:

- 공통:
  - `searchday`
  - `from_time`
  - `to_time`
  - `airport_code`
  - `f_id`
  - `flight_id`
  - `line`
  - `serviceKey`
  - `pageNo`
  - `numOfRows`
- 도착 전용 추가:
  - `airport`
  - `dep_airport_code`
  - `dep_airport`
  - `fgenTime`
- 출발 전용 추가:
  - `airport`
  - `arr_airport_code`
  - `arr_airport`
  - `fgenTime`

### 6.2 KAC 항공기 기종/등록번호

- `schStTime`
- `schEdTime`
- `schAirCode`
- `schFID`
- `schFln`
- `Line`
- `schAPLno`
- `schAPM`
- `serviceKey`
- `pageNo`
- `numOfRows`

### 6.3 IIAC 상세 여객편

- `serviceKey`
- `pageNo`
- `numOfRows`
- `type`
- `searchday`
- `from_time`
- `to_time`
- `airport_code`
- `f_id`
- `flight_id`
- `lang`
- `inqtimechcd`

`inqtimechcd`:

- `E`: 변경/예정시간 기준
- `S`: 스케줄 시간 기준

`lang`:

- `K`: 한국어
- `E`: 영어
- `C`: 중국어
- `J`: 일본어

### 6.4 IIAC 입국장 혼잡도

- `serviceKey`
- `numOfRows`
- `pageNo`
- `terno`
- `airport`
- `type`

### 6.5 IIAC 승객예고

- `selectdate`
- `type`
- `serviceKey`
- `numOfRows`
- `pageNo`

## 7. HTTP 계층 규칙

- HTTP transport는 `httpx.Client` / `httpx.AsyncClient` 기반입니다.
- KAC/IIAC를 분리한 provider adapter를 둡니다.
- 재시도는 `429`, `500`, `502`, `503`, `504`만 허용합니다.
- 인증 오류는 재시도하지 않습니다.
- 서비스키는 로그에 남기지 않습니다.
- IIAC는 가능하면 `type=json` 우선 요청합니다.
- KAC XML 응답은 `_xml.py` 한 곳에서만 파싱합니다.
- Windows에서 `ZoneInfo("Asia/Seoul")`가 실패할 수 있으므로 `tzdata`를 의존성에 포함하고, 런타임에는 UTC+9 fallback을 둡니다.

## 8. 예외 계층

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

매핑 원칙:

- HTTP 401/403 -> `KrairportAuthError`
- HTTP 429 -> `KrairportRateLimitError`
- HTTP 5xx -> `KrairportServerError`
- XML/JSON 파싱 실패 -> `KrairportParseError`
- 지원하지 않는 기능/공항 조합 -> `UnsupportedAirportError`
- 잘못된 파라미터 조합 -> `KrairportRequestError`

## 9. 테스트 규칙

기본 오프라인 테스트:

- 공항코드 -> provider 라우팅
- `ICN`이 KAC로 가지 않는지 검증
- KAC XML `items.item` 단일 dict / list 정규화
- IIAC JSON `items.item` 단일 dict / list 정규화
- 과학적 표기 시간 파싱
- `Flight` 공통 필드 정규화
- KAC `aircraft_assignments`의 등록번호/기종 매핑
- IIAC `arrival_congestion`의 인원수 타입 변환
- `passenger_forecast`의 구역별 합계 필드 변환
- CLI JSON 직렬화와 public export
- coverage gate: `--cov=krairport --cov-fail-under=85`
- API 커버리지 문서: `docs/api-coverage.md`
- enum/type/좌표 표준화: `docs/coordinates-and-types.md`
- 좌표 DMS/decimal 변환, GeoJSON 순서, 근접 공항 계산

Live 테스트:

- `@pytest.mark.live_kac`
- `@pytest.mark.live_iiac`
- 키가 없으면 skip
- 값 자체보다 응답 shape/type만 검증

## 10. 반복 실수 금지 규칙

1. `ICN`을 KAC 공항처럼 처리하지 않습니다.
2. KAC XML 응답을 JSON처럼 가정하지 않습니다.
3. `airport_code`, `schAirCode`, `airport`를 같은 뜻으로 취급하지 않습니다.
4. IIAC `당일 Odp`와 `상세 DeOdp`를 같은 스키마로 가정하지 않습니다.
5. 시간 문자열 `2400`을 무조건 일반 시각으로 파싱하지 않습니다.
6. `f_id`와 `flight_id`를 혼동하지 않습니다.
7. 승객예고는 "예상치", 입국장 혼잡도는 "실시간성 현황"이라는 의미 차이를 유지합니다.
8. 주차요금과 주차현황은 서로 다른 도메인 모델로 유지합니다.
9. `PlaceCoordinate` public DTO의 `(lat, lon)` 순서를 GeoJSON용 `(lon, lat)` 순서와 섞지 않습니다.
10. enum을 추가해도 기존 문자열 비교/직렬화 호환성을 깨지 않습니다.

## 11. 문서 업데이트 규칙

- `README.md`: 사용자용 개요와 예시
- `krairport-api.md`: 공급자/엔드포인트/타입 규칙
- `SKILL.md`: AI 구현 가이드
- `docs/testing.md`: fixture, marker, live test 정책
- `docs/coordinates-and-types.md`: enum/type/좌표/공항 메타데이터 정책
- `docs/repeated-mistakes.md`: 재발 방지 규칙
- `docs/troubleshooting.md`: 운영 중 자주 보는 오류와 해결책
- `AGENTS.md`: 에이전트 작업 라우팅, 모듈 소유권, 검증 기준

문서 작성 규칙:

- 파일 위치 정보는 프로젝트 기준 상대 경로로 작성합니다. 예: `src/krairport/client.py`, `docs/testing.md`
- Python 내부 문서(module/class/function docstring과 설명용 주석)는 한글로 작성합니다.
- provider 원문, 코드 식별자, 명령어, URL은 원문을 유지합니다.

## 12. 출처

확인일: 2026-05-06

- KAC 서비스 목록: https://openapi.airport.co.kr/service
- KAC 실시간 항공운항 상세: https://www.data.go.kr/data/15113771/openapi.do
- KAC 항공기 기종/등록번호: https://www.data.go.kr/data/15144867/openapi.do
- KAC 주차요금: https://www.data.go.kr/data/15038474/openapi.do
- IIAC 상세 여객편: https://www.data.go.kr/data/15112968/openapi.do
- IIAC 당일 여객편(다국어): https://www.data.go.kr/data/15095093/openapi.do
- IIAC 주차 정보: https://www.data.go.kr/data/15095047/openapi.do
- IIAC 입국장현황: https://www.data.go.kr/data/15095061/openapi.do
- IIAC 승객예고: https://www.data.go.kr/data/15095066/openapi.do
- OurAirports data downloads: https://ourairports.com/data/
