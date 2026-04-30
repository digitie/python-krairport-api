# krairport API 명세

`pykrairport`는 한국공항공사(KAC)와 인천국제공항공사(IIAC) OpenAPI를 통합하는 Python 라이브러리입니다. 이 문서는 `0.1.0` 구현과 이후 확장의 public API, 공급자 라우팅, 타입 변환, 테스트 기준을 고정하기 위한 명세입니다.

## 1. 범위

`0.1.0` 범위는 다음 3개 도메인으로 제한합니다.

1. 운항 조회
2. 주차 정보
3. 인천공항 혼잡도/승객예고

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

- Base service family: `http://apis.data.go.kr/B551177/...`
- 인증 파라미터: `serviceKey`
- 응답 형식: JSON + XML
- 공항 범위: **인천공항 전용**
- 추가 공통 파라미터: `type=json|xml`

### 2.3 라우팅 규칙

- `ICN` 요청은 IIAC만 허용
- `ICN` 이외 공항의 운항/주차요금 요청은 KAC 우선
- `arrival_congestion`, `passenger_forecast`, `parking_status`는 IIAC 전용
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
    session: requests.Session | None = None,
)

KrairportClient.from_env(
    kac_name: str = "KAC_SERVICE_KEY",
    iiac_name: str = "IIAC_SERVICE_KEY",
)
```

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

## 4. 모델 규칙

모든 public 모델은:

- `@dataclass(frozen=True, slots=True)`
- 공급자 원본 스키마를 그대로 흘리지 않음
- 디버깅용 `raw: dict`는 유지 가능

필수 모델:

```text
Flight
AircraftAssignment
ParkingFee
ParkingAreaStatus
ArrivalCongestion
PassengerForecast
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
- 비율/거리/소수값이 있는 경우만 `float`
- 빈 문자열, 공백, `-`: `None`

### 5.3 문자열 유지 규칙

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
- coverage gate: `--cov=pykrairport --cov-fail-under=85`

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

## 11. 문서 업데이트 규칙

- `README.md`: 사용자용 개요와 예시
- `krairport-api.md`: 공급자/엔드포인트/타입 규칙
- `SKILL.md`: AI 구현 가이드
- `docs/testing.md`: fixture, marker, live test 정책
- `docs/repeated-mistakes.md`: 재발 방지 규칙
- `docs/troubleshooting.md`: 운영 중 자주 보는 오류와 해결책

## 12. 출처

확인일: 2026-04-30

- KAC 서비스 목록: https://openapi.airport.co.kr/service
- KAC 실시간 항공운항 상세: https://www.data.go.kr/data/15113771/openapi.do
- KAC 항공기 기종/등록번호: https://www.data.go.kr/data/15144867/openapi.do
- KAC 주차요금: https://www.data.go.kr/data/15038474/openapi.do
- IIAC 상세 여객편: https://www.data.go.kr/data/15112968/openapi.do
- IIAC 당일 여객편(다국어): https://www.data.go.kr/data/15095093/openapi.do
- IIAC 주차 정보: https://www.data.go.kr/data/15095047/openapi.do
- IIAC 입국장현황: https://www.data.go.kr/data/15095061/openapi.do
- IIAC 승객예고: https://www.data.go.kr/data/15095066/openapi.do
