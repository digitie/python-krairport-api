# AI 에이전트 가이드: python-krairport-api

이 라이브러리를 사용하여 코드를 작성하는 외부 AI 코딩 어시스턴트(Cursor, Copilot, ChatGPT 등)를 위한 컨텍스트 및 가이드라인 문서입니다.

> **이 저장소 자체를 수정하는 컨트리뷰터/에이전트는 다른 문서를 봅니다**: [`CLAUDE.md`](./CLAUDE.md)가 세션 진입점이며, 컨트리뷰터 가이드라인은 [`AGENTS.md`](./AGENTS.md), 한글 상세 매뉴얼은 [`SKILL.md`](./SKILL.md)에 있습니다. 이 문서는 **소비자 앱**(이 라이브러리를 import해서 사용하는 외부 애플리케이션)을 생성하는 AI를 위한 가이드입니다.

## 이 라이브러리는 무엇인가

- 한국공항공사(KAC)와 인천국제공항공사(IIAC) 공항 OpenAPI의 차이점을 극복하고, 단일한 인터페이스로 조작할 수 있도록 묶어 제공하는 비공식 Python 클라이언트 라이브러리입니다.
- **제공 범위**: 공항 운항 현황(출발/도착), 스케줄, 주차장 현황, 주차 요금 계산, 혼잡도 예측, 버스/택시 정보, 공항 시설물 정보, 번들 공항 메타데이터 및 근접 공항 계산 유틸리티.
- **제공하지 않는 범위**: DB 저장, UI 레이아웃, 모니터링 감사 로그 등 비즈니스 도메인 로직은 소비자 애플리케이션의 몫입니다.

## 아키텍처 및 코딩 규칙

- **Pydantic v2 준수**: 모든 public 응답은 Pydantic v2 기반의 frozen immutable 모델(`KrairportModel` 상속)과 `StrEnum`으로 제공됩니다. 직렬화 시에는 `model_dump(mode="json")` 또는 `model_dump_json()`을 권장합니다.
- **시간 정책**: 모든 시간 데이터는 KST(한국 표준시) 기준으로 파싱 및 보존됩니다. Windows 환경을 위해 `tzdata` 패키지가 런타임 의존성으로 포함되어 있습니다.
- **좌표 시스템**: WGS84 decimal degrees 기준의 `krairport.Coordinate` 클래스를 이용합니다. GeoJSON 변환 등이 필요한 경우 순서에 유의하십시오.
- **주소 정보**: 공급자 API 응답에 주소 필드가 명확히 존재할 때만 `str | None` 문자열로 보존하며, 단순한 공항 내부 명칭이나 시설 위치 문자열을 주소로 유추하여 채워넣지 않습니다.

## 주요 인터페이스 표면

### `KrairportClient`

```python
from krairport import KrairportClient

# 직접 API 키 전달을 통한 인스턴스화
client = KrairportClient(
    kac_service_key="YOUR_KAC_KEY",
    iiac_service_key="YOUR_IIAC_KEY",
    timeout=10.0,
    retries=3
)

# 환경 변수(DATA_GO_KR_SERVICE_KEY)를 자동으로 읽어 인스턴스화
client = KrairportClient.from_env()
```

### 주요 통합 메서드

- `departures(airport_code: str, ...)`: 해당 공항의 출발 항공편 현황 정보.
- `arrivals(airport_code: str, ...)`: 해당 공항의 도착 항공편 현황 정보.
- `flight_schedules(airport_code: str, ...)`: 운항 스케줄 정보 (KAC / IIAC 별도 제공 연동).
- `parking_status(airport_code: str)`: 주차장 혼잡 상태 조회.
- `parking_fees(airport_code: str, ...)`: KAC 전용 주차 요금 계산 연동.
- `nearest_airport(coordinate: Coordinate, ...)`: 입력 좌표와 가장 근접한 한국 공항 검색.

## 피해야 할 실수 (AI 어시스턴트 주의사항)

1. **라우팅 미스매치**:
   - 인천공항(`ICN`) 관련 요청은 KAC API에 보낼 수 없으며, 국내 공항 요청은 IIAC API에 보낼 수 없습니다. 라이브러리 내부에서 라우팅하여 적절하지 않은 조합일 경우 `UnsupportedAirportError`가 발생하므로, 사전에 공항 코드를 철저히 검증하십시오.
2. **좌표 순서**:
   - `Coordinate.as_tuple()`과 `as_lat_lon()`은 `(latitude, longitude)` 순서입니다.
   - 반면 GeoJSON 규격을 지원하는 `as_geojson_position()`은 `(longitude, latitude)` 순서로 반환하므로 순서가 바뀌지 않도록 각별히 유의하십시오.
3. **인증키 하드코딩**:
   - 절대 `DATA_GO_KR_SERVICE_KEY` 등의 API 키를 소스 코드나 깃 피스처에 노출하지 마십시오. 반드시 환경 변수 또는 보안 설정 시스템을 사용하십시오.
4. **원시 필드 노출 방지**:
   - API가 반환하는 raw JSON의 `airport_code`, `airport`, `schAirCode`, `apcd` 같은 명칭을 public 인터페이스에 흘리지 마십시오. 라이브러리가 정규화하여 제공하는 `provider`, `airport_code`, `flight_id` 등의 필드를 정석대로 활용해야 합니다.
