# Changelog

## Unreleased

- HTTP transport를 `requests`에서 `httpx` 기반 sync/async client로 전환.
- `AsyncKrairportClient`, `KrairportClient.aio()`, context manager, `KrairportConfig` 추가.
- `from_env()`가 process env와 로컬 `.env` / `.env.local`의 서비스키를 공백 제거 후 로드하도록 보강.
- `python-krtour-map` 연동을 위해 `PROVIDER_NAME`, `PaginatedResult`, `iter_pages(...)`, provider raw 보존 계약을 문서화.

- `DebugRun`, `KrairportClient.debug()`, fixture replay runner, Streamlit debug UI fixture writer 문서와 테스트 추가
- `api_catalog()`와 서비스키 신청 링크 포함 API 카탈로그 추가

- 배포/저장소 이름을 `python-krairport-api`, import 패키지 이름을 `krairport`로 정리하고 `src/krairport` 레이아웃으로 이동
- 좌표 public surface를 `kraddr.base.PlaceCoordinate` 직접 사용 방식으로 변경
- `krairport.geo` 좌표 wrapper/helper 제거
- 시설 주소 public surface를 `kraddr.base.Address` 직접 사용 방식으로 추가

## 0.1.0 - 2026-04-30

- `README.md` 작성
- `krairport-api.md` 작성
- `SKILL.md` 작성
- `docs/testing.md`, `docs/repeated-mistakes.md`, `docs/troubleshooting.md` 추가
- `KrairportClient`, KAC/IIAC provider adapter, HTTP 계층, XML/JSON item 정규화 구현
- `Flight`, `AircraftAssignment`, `ParkingFee`, `ParkingAreaStatus`, `ArrivalCongestion`, `PassengerForecast` 모델 추가
- KST datetime 파서, 과학적 표기 timestamp 처리, Windows `tzdata` fallback 추가
- CLI 엔트리포인트 추가
- KAC 스케줄, 주차현황, 시설, 버스, 제주 택시대기 API 추가
- IIAC 스케줄, 취항도시, 기상, 택시, 버스, 시설 API 추가
- KAC/IIAC raw item access 추가
- KAC 공식 서비스 목록과 IIAC 공공데이터포털 변경 공지를 반영한 API 커버리지 문서 추가
- 외부 프로그램 연동용 `StrEnum`, type alias, WGS84 `Coordinate`, 공항 메타데이터 레지스트리 추가
- public 응답 모델을 Pydantic v2 `BaseModel` 기반 immutable 모델로 전환
- `AGENTS.md` 추가, 문서 경로 상대 표기와 Python 내부 문서 한글 작성 규칙 반영
- Windows 작업 환경의 `rg` 권한 문제와 PowerShell UTF-8 출력 깨짐 대응 규칙 문서화
- fixture 기반 테스트 74개 추가, coverage fail-under 85 기준 통과
