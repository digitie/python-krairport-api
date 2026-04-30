# 문제 해결

## `KrairportAuthError`

확인할 것:

- `KAC_SERVICE_KEY`, `IIAC_SERVICE_KEY`가 올바른지
- 활용신청이 승인되었는지
- URL 인코딩된 키를 다시 인코딩하고 있지 않은지

## `UnsupportedAirportError`

대표 사례:

- `ICN`을 KAC-only 엔드포인트에 전달
- 인천공항 혼잡도 API에 `GMP` 같은 공항을 넘김

해결:

- 통합 메서드에서는 `airport_code`만 넘기고 provider를 직접 강제하지 않음
- low-level provider 메서드 사용 시 공항 범위를 먼저 확인

## `KrairportParseError`

대표 원인:

- KAC XML 구조가 단일 item / 배열 item 사이에서 바뀜
- IIAC 시간이 과학적 표기 문자열처럼 내려옴
- 공급자 문서와 실제 필드명이 약간 다름

해결:

- fixture로 재현 후 parser 보강
- `raw` payload를 확인해 실제 필드명 기준으로 수정

## `ZoneInfoNotFoundError: Asia/Seoul`

Windows 환경에서 `tzdata`가 설치되지 않았을 때 발생할 수 있습니다.

해결:

- `pip install -e ".[dev]"`로 `tzdata` 의존성을 설치
- 설치 전 실행에서도 `_time.py`는 UTC+9 fallback을 사용하므로 최신 코드인지 확인

## 결과가 비어 있음

확인할 것:

- `searchday`, `from_time`, `to_time` 범위가 실제 데이터 창과 맞는지
- IIAC 당일 API에 과거/미래 날짜를 넣고 있지 않은지
- 상세 API가 필요한데 당일 API를 사용하고 있지 않은지

## 주차 데이터가 예상과 다름

- KAC `parking_fees()`는 요금표 성격
- IIAC `parking_status()`는 주차면/주차대수 현황 성격

같은 "주차"라도 비교 가능한 값이 아닐 수 있습니다.
