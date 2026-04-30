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
- fixture 기반 테스트 53개 추가, coverage fail-under 85 기준 통과
