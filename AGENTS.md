# AGENTS.md

## 역할

이 문서는 `krairport`에서 작업하는 Codex/agent를 위한 운영 가이드입니다. `pykma`, `pyopinet`, `pykex`의 작업 방식처럼 빠르게 방향을 잡기 위한 문서이며, 세부 API 명세와 구현 규칙은 작업 주제에 맞춰 `krairport-api.md`, `SKILL.md`, `docs/` 아래 문서를 함께 확인합니다.

## 지시 우선순위

1. 사용자 요청
2. 이 `AGENTS.md`
3. `krairport-api.md`
4. `SKILL.md`
5. `README.md`
6. 기존 코드와 테스트
7. 최소한의, 되돌릴 수 있는 가정

문서가 충돌하면 더 높은 우선순위의 문서를 따르고, 낮은 우선순위 문서를 같은 변경에서 갱신합니다.

## 프로젝트 기준

- `krairport`는 한국공항공사(KAC)와 인천국제공항공사(IIAC) 공항 OpenAPI를 통합하는 비공식 Python 클라이언트입니다.
- `ICN`은 IIAC, 그 외 지원 공항은 KAC로 라우팅합니다.
- public 응답은 Pydantic v2 기반 immutable 모델과 `StrEnum`으로 제공합니다.
- 공항 좌표는 `kraddr.base.PlaceCoordinate`, 시설 주소는 `kraddr.base.Address`를 파라미터와 반환 모델에 직접 사용합니다.
- KAC는 XML-heavy, IIAC는 JSON 우선 호출을 기본으로 합니다.
- 런타임 의존성은 `httpx`, `pydantic`, `kraddr.base`, Windows용 `tzdata`입니다.
- 기본 테스트는 실제 KAC/IIAC 네트워크 호출 없이 동작해야 합니다.

## Provider API 사용 원칙

- 외부 API 관련 작업은 다른 구현보다 먼저 wrapper/adapter/gateway 지양 원칙을 확인하고 문서/코드에 반영한 뒤 진행합니다.
- downstream이 직접 사용할 안정된 public client, typed model, enum, helper를 제공합니다.
- 단순 전달용 wrapper, 장기 호환 alias, 임시 facade를 만들지 않습니다.
- TripMate나 `python-krtour-map`에서 필요한 endpoint, pagination, cursor, exception, raw payload 계약이 부족하면 이 저장소의 public API를 먼저 안정화합니다.
- `python-krtour-map` 호환성은 provider public client 직접 호출, `raw` 보존, `model_dump(mode="json")`, `iter_pages(...)`, canonical `PROVIDER_NAME` 노출을 기준으로 합니다.
- 다른 라이브러리에 검증된 구현이 있으면 wrapper로 감싸지 말고 라이선스와 출처를 확인한 뒤 현재 구조에 직접 반영합니다.

## 구현 방향

- 불필요한 wrapper나 호환층을 새로 만들지 않습니다. 좌표와 주소는 `krairport` wrapper 없이 `kraddr.base.PlaceCoordinate`, `kraddr.base.Address`를 직접 import해 씁니다.
- `pykma`, `pyopinet`, `pykex` 또는 가까운 유지보수 라이브러리에 이미 검증된 구현 패턴이 있으면, 작은 local patch로 우회하지 말고 그 구현 방향을 `krairport` 코드에 직접 적용합니다.
- 최소 수정은 기본 작업 습관이지만, 검증된 구현을 따르는 것이 장기 유지보수와 일관성을 높이면 더 큰 변경도 허용합니다. 이때 변경 범위, 문서, 테스트를 함께 맞춥니다.
- 다른 라이브러리 구현을 참고할 때도 provider-native 이름, 인증키, 응답 스키마를 그대로 public surface로 흘리지 않고 `krairport`의 모델/예외/라우팅 규칙에 맞춰 흡수합니다.

## 문서/경로 규칙

- 문서의 파일 위치 정보는 항상 프로젝트 기준 상대 경로로 씁니다. 예: `src/krairport/client.py`, `docs/testing.md`.
- 로컬 절대 경로, 사용자 홈 경로, 드라이브 경로는 문서에 쓰지 않습니다.
- 프로젝트 문서는 한글로 작성합니다.
- Python 내부 문서도 한글로 작성합니다. 모듈 docstring, class/function docstring, 설명용 주석은 한글을 기본으로 하고, provider 원문/코드 식별자/URL만 원문을 유지합니다.
- public API 변경 시 `README.md`, `krairport-api.md`, `SKILL.md`, 관련 `docs/` 문서를 함께 갱신합니다.

## 로컬 작업 환경 규칙

- 이 Windows 환경에서는 `rg` 실행 권한 문제가 반복될 수 있습니다. 막히면 권한 조정이나 재시도에 시간을 쓰지 말고 PowerShell `Get-ChildItem` / `Select-String` 조합으로 우회합니다.
- 한글 문서를 PowerShell에서 읽거나 검색할 때는 `Get-Content -Encoding UTF8`, `Select-String -Encoding UTF8`처럼 인코딩을 명시합니다.
- PowerShell 출력이 깨져 보여도 먼저 UTF-8 인코딩 누락을 의심합니다. 문서 자체가 깨졌다고 판단하기 전에 `-Encoding UTF8`로 다시 확인합니다.

## 문서 라우팅

- `README.md`: 사용자용 개요, 설치, 예제, 모델 요약.
- `krairport-api.md`: 공급자 경계, endpoint, 타입 변환, 모델 규칙.
- `docs/api-coverage.md`: typed/raw API 지원 범위.
- `docs/coordinates-and-types.md`: Pydantic 모델, enum/type alias, 좌표, 공항 메타데이터.
- `docs/testing.md`: fixture, coverage, live test 정책.
- `docs/troubleshooting.md`: 사용자에게 보이는 실패와 해결책.
- `docs/repeated-mistakes.md`: 이미 겪었거나 반복되기 쉬운 실수.
- `SKILL.md`: 에이전트용 구현 불변조건과 체크리스트.
- `AGENTS.md`: 작업 라우팅, 모듈 소유권, 검증 체크리스트.
- `CHANGELOG.md`: 릴리스 관점 변경 이력.
- `pyproject.toml`: 패키징, 의존성, lint/test 설정.

## 모듈 지도

- `src/krairport/client.py`: 통합 `KrairportClient`, provider 라우팅, 사용자용 메서드.
- `src/krairport/providers/kac.py`: 한국공항공사 REST/XML provider adapter.
- `src/krairport/providers/iiac.py`: 인천국제공항공사 B551177 JSON provider adapter.
- `src/krairport/models.py`: public Pydantic 응답 모델과 `KrairportModel`.
- `src/krairport/enums.py`: provider, direction, airport, language, schedule enum.
- `src/krairport/types.py`: 외부 wrapper용 type alias.
- `src/krairport/airports.py`: 번들 공항 메타데이터와 근접 공항 helper.
- 좌표 정규화, DMS 파싱, 거리 계산은 `kraddr.base.PlaceCoordinate`와 `kraddr.base.coordinates`를 직접 사용합니다.
- 주소 정규화는 `kraddr.base.Address`를 직접 사용합니다.
- `src/krairport/_http.py`: session, retry, HTTP/body-level error mapping.
- `src/krairport/_xml.py`: KAC-style XML parsing과 item normalization.
- `src/krairport/_time.py`: KST-aware datetime 파싱.
- `src/krairport/_convert.py`: 응답 경계의 작은 타입 변환 helper.
- `src/krairport/_routing.py`: 공항코드별 provider 결정과 조합 검증.
- `src/krairport/cli.py`: JSON CLI 출력.
- `tests/`: 네트워크 없는 단위 테스트와 fixture.

## 반드시 지킬 것

- 실제 `serviceKey`, API 키, 인증 토큰은 코드, fixture, 로그, 문서에 남기지 않습니다.
- 기본 테스트에서 실제 API를 호출하지 않습니다.
- `ICN`을 KAC로 보내지 않습니다.
- KAC XML 응답을 JSON처럼 가정하지 않습니다.
- IIAC-only API에 비-`ICN` 공항을 조용히 허용하지 않습니다.
- `airport_code`, `airport`, `schAirCode`, `apcd` 같은 provider-native 이름을 public 모델에 그대로 흘리지 않습니다.
- 편명, 공항코드, 내부 flight unique id처럼 선행 0이나 문자열 의미가 있는 값은 `int`로 변환하지 않습니다.
- 좌표 순서를 섞지 않습니다. `PlaceCoordinate.as_tuple()`과 `as_lat_lon()`은 `(latitude, longitude)`, `as_geojson_position()`은 `(longitude, latitude)`입니다.
- 공항 내부 위치 문자열을 주소로 추정하지 않습니다. provider row에 주소 필드가 있을 때만 `Address.from_mapping()`을 직접 사용합니다.
- public enum은 `StrEnum`으로 유지해 문자열 비교와 JSON 직렬화 호환성을 깨지 않습니다.
- public 응답 모델은 `KrairportModel` 기반 Pydantic 모델로 유지하고, 직렬화는 `model_dump(mode="json")`, `model_dump_json()`, `to_dict()`, `to_json()`을 사용합니다.

## 작업 소유권

### Provider 라우팅과 통합 클라이언트

담당 파일:

- `src/krairport/client.py`
- `src/krairport/_routing.py`
- `tests/test_client.py`
- `tests/test_routing.py`

확인할 것:

- `provider_for_airport("ICN")`은 IIAC입니다.
- KAC 공항은 KAC로 라우팅합니다.
- 잘못된 기관-공항 조합은 `UnsupportedAirportError`입니다.
- 새 public 메서드는 README와 명세에 예시/반환 타입을 반영합니다.

### KAC adapter

담당 파일:

- `src/krairport/providers/kac.py`
- `src/krairport/_xml.py`
- `tests/test_kac.py`

확인할 것:

- 인증 파라미터는 `serviceKey`입니다.
- XML `items.item`은 단일 dict와 list를 모두 처리합니다.
- KAC raw access는 `service`/`operation` path component를 검증합니다.
- `ICN` 요청은 KAC endpoint에서 거부합니다.

### IIAC adapter

담당 파일:

- `src/krairport/providers/iiac.py`
- `tests/test_iiac.py`

확인할 것:

- 가능하면 `type=json`을 요청합니다.
- B551177 service/operation URL 조립을 안전하게 유지합니다.
- IIAC-only method는 `ICN`만 허용합니다.
- data.go.kr 변경 공지가 있는 endpoint는 `docs/api-coverage.md`에 상태를 남깁니다.

### 모델, enum, 타입, 좌표

담당 파일:

- `src/krairport/models.py`
- `src/krairport/enums.py`
- `src/krairport/types.py`
- `src/krairport/airports.py`
- `docs/coordinates-and-types.md`
- `tests/test_pydantic_models.py`
- `tests/test_geo.py`
- `tests/test_airports.py`

확인할 것:

- Pydantic 모델은 frozen이고 unknown field를 거부합니다.
- `Provider`, `Direction`은 문자열 비교가 유지됩니다.
- 좌표는 WGS84 decimal degrees이며 범위 검증을 통과해야 합니다.
- `krairport` 안에 좌표/주소 wrapper/helper를 만들지 않고 `PlaceCoordinate.from_mapping()`, `Address.from_mapping()` 같은 kraddr.base API를 직접 호출합니다.
- 공항 메타데이터는 앱 지도/검색 편의용이며 항법용 공식 원천으로 안내하지 않습니다.

### HTTP, 에러, 변환

담당 파일:

- `src/krairport/_http.py`
- `src/krairport/_convert.py`
- `src/krairport/_time.py`
- `src/krairport/exceptions.py`
- `tests/test_http.py`
- `tests/test_convert.py`
- `tests/test_time.py`

확인할 것:

- HTTP 401/403, 429, 4xx, 5xx 매핑을 공통 예외 계층으로 유지합니다.
- body-level `resultCode` 실패를 빈 성공으로 반환하지 않습니다.
- `2400`, `YYYYMMDDHHMM`, 과학적 표기 timestamp를 KST 기준으로 처리합니다.
- 빈 문자열, 공백, `-`는 `None`으로 정규화합니다.

### 문서

담당 파일:

- 모든 `.md` 문서
- Python docstring과 설명용 주석

확인할 것:

- 문서는 한글로 작성합니다.
- 파일 위치는 프로젝트 기준 상대 경로만 사용합니다.
- Python 내부 문서도 한글로 작성합니다.
- 코드 식별자, 명령어, provider endpoint, URL은 원문을 유지합니다.
- 새 실수나 함정은 `docs/repeated-mistakes.md`와 `SKILL.md`에 반영합니다.

## 검증 기준

기본 검증:

```bash
python -m compileall src/krairport tests
python -m pytest
python -m pytest --cov=krairport --cov-fail-under=85
```

정적 검증:

```bash
python -m ruff check .
python -m mypy src/krairport
```

Skill 문서를 변경했으면 다음도 실행합니다.

```bash
python -X utf8 <skill-creator>/scripts/quick_validate.py .
```

실제 API 테스트는 opt-in으로만 둡니다.

```bash
pytest -m live_kac
pytest -m live_iiac
```

## 커밋 위생

- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `__pycache__`, virtual environment는 커밋하지 않습니다.
- 커밋은 되돌리기 쉬운 단위로 유지합니다.
- 리모트 푸시 전 `git status --short --branch`로 작업트리를 확인합니다.
