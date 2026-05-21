# 테스트 정책

## Debug UI fixture replay

디버그 UI에서 저장한 JSON fixture는 `tests/fixtures/{function}/{case}.json`에 둡니다.
`tests/test_generated_fixtures.py`는 이 파일들을 자동으로 읽고, 저장된
`response.body`를 `tests/runners.py`의 parser에 다시 넣어 `processed`와 비교합니다.

기본 실행:

```powershell
python -m pytest tests/test_generated_fixtures.py
```

지원 assertion mode:

- `snapshot`: `processed` 전체 비교, `exclude_fields` 적용
- `schema_only`: parser/processor 성공 여부만 확인
- `required_fields`: 지정 필드 존재 여부 확인
- `count`: 결과 개수 비교

새 fixture 대상 public 함수가 늘어나면 `tests/runners.py`의 `RUNNERS`에 parser와
processor를 추가하고, 민감정보는 fixture 저장 전에 `<REDACTED>`로 마스킹합니다.
상세 포맷은 `docs/debug-fixtures.md`에 정리합니다.

`krairport` 테스트는 기본적으로 **네트워크 없이** 돌아가야 합니다. KAC와 IIAC 모두 일별 트래픽 제한이 있고, 운항/혼잡도 데이터는 시점에 따라 쉽게 달라지므로 fixture 기반 테스트가 기본입니다.

## 원칙

- 기본 `pytest` 실행은 실 API를 호출하지 않습니다.
- 모든 provider 테스트는 고정 fixture 또는 mock response를 사용합니다.
- live 테스트는 별도 marker로만 실행합니다.
- 타입 assertion을 반드시 포함합니다.
- 현재 기준선은 `90 passed`, `2 skipped`, coverage fail-under `85`입니다.

## 필수 오프라인 테스트

### 라우팅

- `ICN` -> IIAC
- `ICN` 이외 공항 -> KAC
- IIAC 전용 메서드에 비-`ICN` 공항코드 전달 시 예외

### 파싱

- KAC XML `items.item`이 dict 하나일 때
- KAC XML `items.item`이 list일 때
- IIAC JSON `items.item`이 dict 하나일 때
- IIAC JSON `items.item`이 list일 때
- 빈 문자열/공백/`-`가 `None`으로 정규화되는지
- `2.02112E+11` 같은 IIAC 시간 예시가 파싱되는지

### 모델 타입

- `Flight.scheduled_at` / `estimated_at`는 aware `datetime`
- `codeshare`는 `bool | None`
- `ParkingFee` 요금 필드는 `int | None`
- `ArrivalCongestion` 인원수 필드는 `int | None`
- `PassengerForecast` 구간 값은 `int | None`
- `Provider` / `Direction`은 `StrEnum`이지만 문자열 비교가 가능해야 함
- public 응답 모델은 Pydantic `BaseModel`이며 frozen field validation과 `model_dump(mode="json")`를 검증
- `kraddr.base.PlaceCoordinate`는 WGS84 decimal degrees, GeoJSON 순서, DMS 파싱을 검증
- `kraddr.base.Address`는 시설 모델에서 직접 반환되고 JSON 직렬화되는지 검증
- `AirportMetadata`는 provider/active 필터와 nearest airport 계산을 검증

## Live 테스트

```bash
pytest -m live_kac
pytest -m live_iiac
pytest --cov=krairport --cov-fail-under=85
```

환경변수:

- `DATA_GO_KR_SERVICE_KEY`
- `.env` / `.env.local`의 `DATA_GO_KR_SERVICE_KEY`

규칙:

- 키가 없으면 skip
- `-m live_kac` 또는 `-m live_iiac`로 명시 실행했을 때만 실제 API 호출
- 라이브 테스트와 `KrairportClient.from_env()`는 process env를 먼저 보고, 없으면 로컬 `.env` 값을 사용합니다.
- 응답 shape와 타입만 검증
- 특정 편명, 주차대수, 혼잡도 수치를 고정값으로 단정하지 않음

## fixture 작성 규칙

- KAC는 실제 XML 응답 구조를 유지합니다.
- IIAC는 실제 JSON 응답 구조를 유지합니다.
- 숫자형 문자열은 fixture 안에서는 원본 문자열 상태를 유지하고, 테스트가 변환 코드를 지나가도록 합니다.
- 서비스키는 반드시 `[REDACTED]` 처리합니다.

## 권장 marker

- `live_kac`
- `live_iiac`
- `integration`

## 회귀 테스트 우선순위

버그를 고칠 때는 항상:

1. 재현 fixture 추가
2. 실패하는 테스트 작성
3. 구현 수정
4. README / 명세 / troubleshooting 반영
