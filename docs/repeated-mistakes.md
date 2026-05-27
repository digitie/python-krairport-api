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
- 가드레일: `pytest --cov=krairport --cov-fail-under=85`를 기본 검증에 포함

## 10. 공식 API 목록 확인 없이 "지원 완료"라고 쓰는 실수

- 증상: 운항/주차 API만 구현하고 통계/시설/교통/기상 API가 누락됨
- 원인: KAC 서비스 목록과 IIAC B551177 데이터셋 목록을 별도로 대조하지 않음
- 가드레일: `docs/api-coverage.md`에 typed/raw 지원 상태를 기록하고, 미모델링 API는 `raw_items`로 접근 가능하게 유지

## 11. raw endpoint access를 너무 열어 두는 실수

- 증상: 임의 URL 또는 path traversal 형태의 service/operation이 들어갈 수 있음
- 원인: service 이름을 그대로 URL에 붙임
- 가드레일: `kac_raw_items()` / `iiac_raw_items()`는 영문/숫자/underscore path component만 허용

## 12. 공공데이터포털 변경 공지를 놓치는 실수

- 증상: 예전 IIAC service/operation 조합을 문서에 남겨 실제 호출이 실패
- 원인: 공공데이터포털은 2026년에도 `FlightClosingInfoSpot`, `statusOfFltacdmmlstnAirTrafficPublic` 같은 변경 공지를 냈음
- 가드레일: 새 IIAC API를 typed 모델로 승격하기 전 `docs/api-coverage.md`와 공공데이터포털 변경 공지를 함께 확인

## 13. 좌표 순서를 섞는 실수

- 증상: 지도에서 공항이 바다나 다른 국가에 표시됨
- 원인: UI용 `(latitude, longitude)`와 저장/GeoJSON용 `(longitude, latitude)` 순서를 혼동
- 가드레일: 좌표는 `krairport.Coordinate`를 쓰고, `as_tuple()`/`as_lat_lon()`과 `as_geojson_position()`을 구분해 테스트로 고정

## 14. enum 도입으로 문자열 호환성을 깨는 실수

- 증상: 기존 사용자의 `flight.provider == "kac"` 비교나 JSON 직렬화가 실패
- 원인: 일반 `Enum`을 반환하거나 모델 필드를 enum-only로 급격히 바꿈
- 가드레일: public enum은 모두 `StrEnum`으로 두고 기존 문자열 비교 테스트를 유지

## 15. 공항 내부 위치를 주소로 오인하는 실수

- 증상: `T1 1F`, `국내선`, `면세구역` 같은 값이 주소 문자열로 직렬화됨
- 원인: provider의 `loc`/`location` 필드를 실제 도로명/지번주소처럼 처리
- 가드레일: 내부 위치는 `AirportFacility.location`에 두고, 주소 필드가 있을 때만 주소 문자열로 보존

## 16. Pydantic 전환 후 dataclass 직렬화를 계속 쓰는 실수

- 증상: CLI나 외부 앱에서 `asdict()`가 더 이상 응답 모델을 dict로 바꾸지 못함
- 원인: public 응답 모델이 Pydantic `BaseModel`로 바뀌었는데 직렬화 경로를 갱신하지 않음
- 가드레일: CLI와 문서 예시는 `model_dump(mode="json")`, `model_dump_json()`, `to_dict()`, `to_json()`을 사용

## 16. 문서에 로컬 절대 경로를 남기는 실수

- 증상: 다른 환경의 에이전트나 사용자가 문서의 파일 위치를 따라갈 수 없음
- 원인: 드라이브 문자나 사용자 홈으로 시작하는 개인 개발환경 경로를 문서에 기록
- 가드레일: 모든 문서의 파일 위치 정보는 `src/krairport/client.py`, `docs/testing.md`처럼 프로젝트 기준 상대 경로만 사용

## 17. Python 내부 문서를 영어로 되돌리는 실수

- 증상: 모듈 docstring, 함수 docstring, 설명용 주석이 문서 정책과 달라짐
- 원인: 기존 예제나 외부 프로젝트에서 영어 docstring을 그대로 가져옴
- 가드레일: Python 내부 문서는 한글로 작성하고, provider 원문/코드 식별자/URL만 원문 유지

## 18. `rg` 권한 문제에 계속 시간을 쓰는 실수

- 증상: Windows 환경에서 `rg`가 실행 권한 문제로 막혀 파일 검색이 지연됨
- 원인: 같은 환경 제약을 매번 새 문제처럼 보고 `rg` 재시도나 권한 조정부터 시도함
- 가드레일: 이 저장소 작업에서는 `Get-ChildItem -Recurse -File`과 `Select-String`으로 바로 우회

## 19. PowerShell에서 UTF-8 문서를 깨진 것으로 오해하는 실수

- 증상: 한글 Markdown이나 Python docstring이 PowerShell 출력에서 깨져 보여 불필요한 수정이 발생
- 원인: PowerShell 기본 출력/입력 인코딩이 UTF-8 문서와 맞지 않음
- 가드레일: 문서와 Python 파일을 읽거나 검색할 때 `Get-Content -Encoding UTF8`, `Select-String -Encoding UTF8`을 사용

## 20. 검증된 구현 위에 불필요한 wrapper를 덧대는 실수

- 증상: `pykma`, `pyopinet`, `pykex` 등에서 이미 정리된 구현 패턴이 있는데도 `krairport`에 얇은 wrapper나 우회 레이어만 추가되어 코드 경로가 늘어남
- 원인: "최소 수정"을 작은 diff로만 해석해 장기적으로 필요한 구조 정리를 미룸
- 가드레일: 가까운 유지보수 라이브러리의 검증된 구현 방향이 있으면 불필요한 wrapper를 만들지 말고 `krairport`의 모델/예외/라우팅 규칙에 맞춰 직접 적용

## 21. src layout 전환 후 패키지 검색 설정을 빼먹는 실수

- 증상: 로컬 테스트나 editable install에서 `ModuleNotFoundError: No module named 'krairport'`가 발생
- 원인: 코드가 `src/krairport`로 이동했는데 `pyproject.toml`의 setuptools `where`나 pytest `pythonpath`가 이전 루트 패키지 기준으로 남아 있음
- 가드레일: `pyproject.toml`에서 `where = ["src"]`, `pythonpath = ["src"]`를 유지하고 검증 명령은 `python -m compileall src/krairport tests`, `python -m mypy src/krairport`를 사용

## 22. KAC 공항코드 목록 API를 smoke test나 public API로 되살리는 실수

- 증상: live 검증에서 `NO OPENAPI SERVICE ERROR.`가 발생하거나 사용하지 않는 `airport_codes()` surface가 다시 생김
- 원인: `AirportCodeList/getAirportCodeList`는 현재 `krairport`에서 사용할 일이 없고, 번들 공항 메타데이터가 같은 목적을 더 안정적으로 처리함
- 가드레일: 공항 목록/메타데이터는 `airports()`, `airport_metadata()`, `nearest_airport()`를 사용하고 KAC 공항코드 목록 typed API와 live smoke를 추가하지 않음
