# 반복 실수 방지 로그

## 1. `ICN`을 KAC 공항으로 보내는 실수

- 증상: 인천공항 조회가 비정상 응답 또는 빈 결과를 반환
- 원인: KAC 데이터셋 다수가 "전국공항(인천공항 제외)" 범위
- 가드레일: 라우팅 테스트에서 `ICN`은 항상 IIAC로만 분기

## 2. KAC 응답을 JSON처럼 가정하는 실수

- 증상: `response["body"]` 같은 JSON 접근에서 실패
- 원인: KAC 핵심 엔드포인트는 XML-only가 아직 많음
- 가드레일: KAC parser는 `_xml.py`에서만 처리

## 3. `airport_code`, `airport`, `schAirCode`를 같은 값처럼 취급하는 실수

- 증상: 필터가 적용되지 않거나 엉뚱한 조회 결과 반환
- 원인: 기관/엔드포인트마다 같은 "공항" 개념을 다른 파라미터명으로 사용
- 가드레일: provider adapter에서만 provider-native 이름 사용

## 4. `flight_id`와 `f_id`를 혼동하는 실수

- 증상: 특정 편명 조회가 실패
- 원인: `flight_id`는 사람이 보는 편명이고 `f_id`는 공급자 내부 UNIQ 코드
- 가드레일: 모델에는 `flight_id`, `flight_unique_id`를 둘 다 둠

## 5. IIAC 승객예고를 실시간 혼잡도로 오해하는 실수

- 증상: 예측치와 현황 데이터를 섞어서 표시
- 원인: 승객예고는 forecast, 입국장현황은 current-like snapshot
- 가드레일: `PassengerForecast`와 `ArrivalCongestion` 모델 분리

## 6. `2400`이나 과학적 표기 시간을 일반 문자열로만 다루는 실수

- 증상: 시간 정렬/비교 오류
- 원인: 공급자 문서와 예시가 일반적인 ISO 포맷이 아님
- 가드레일: `_time.py`에 통합 파서 두고 테스트 고정

## 7. 주차요금과 주차현황을 같은 스키마로 합치려는 실수

- 증상: 필드가 과도하게 nullable해지고 모델 의미가 흐려짐
- 원인: KAC 주차요금은 정적 규칙, IIAC 주차정보는 실시간 현황
- 가드레일: `ParkingFee`와 `ParkingAreaStatus`를 분리

## 8. Windows에서 `Asia/Seoul` timezone이 항상 있다고 가정하는 실수

- 증상: 테스트 수집 단계에서 `ZoneInfoNotFoundError: No time zone found with key Asia/Seoul`
- 원인: Windows Python 환경에는 IANA timezone database가 기본 포함되지 않을 수 있음
- 가드레일: `tzdata`를 Windows 의존성에 추가하고, `_time.py`에서 UTC+9 fallback 제공

## 9. coverage 기준 없이 테스트 수만 늘리는 실수

- 증상: happy path 테스트는 많지만 CLI, 예외 경로, 변환 helper가 방치됨
- 원인: 테스트 개수만 보고 위험한 분기 coverage를 확인하지 않음
- 가드레일: `pytest --cov=pykrairport --cov-fail-under=85`를 기본 검증에 포함
