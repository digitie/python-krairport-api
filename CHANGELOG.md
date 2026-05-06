# Changelog

## 0.1.0 - 2026-04-30

- `README.md` 작성
- `krairport-api.md` 작성
- `SKILL.md` 작성
- `docs/testing.md`, `docs/repeated-mistakes.md`, `docs/troubleshooting.md` 추가
- `KrairportClient`, KAC/IIAC provider adapter, HTTP 계층, XML/JSON item 정규화 구현
- `Flight`, `AircraftAssignment`, `ParkingFee`, `ParkingAreaStatus`, `ArrivalCongestion`, `PassengerForecast` 모델 추가
- KST datetime 파서, 과학적 표기 timestamp 처리, Windows `tzdata` fallback 추가
- CLI 엔트리포인트 추가
- KAC 공항코드, 스케줄, 주차현황, 시설, 버스, 제주 택시대기 API 추가
- IIAC 스케줄, 취항도시, 기상, 택시, 버스, 시설 API 추가
- KAC/IIAC raw item access 추가
- KAC 공식 서비스 목록과 IIAC 공공데이터포털 변경 공지를 반영한 API 커버리지 문서 추가
- 외부 프로그램 연동용 `StrEnum`, type alias, WGS84 `Coordinate`, 공항 메타데이터 레지스트리 추가
- fixture 기반 테스트 71개 추가, coverage fail-under 85 기준 통과
