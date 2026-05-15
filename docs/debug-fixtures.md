# Debug UI와 fixture replay

`krairport`의 디버그 UI는 운영용 대시보드가 아니라 테스트 자산 생성 도구입니다.
UI에서 public client 함수를 실행한 뒤 raw response 후보, Pydantic 모델, processed 결과,
trace, error를 분리해 보고 의미 있는 케이스만 JSON fixture로 저장합니다.

## 구조

```text
src/krairport/debug.py
tests/fixtures/{function}/{case}.json
tests/runners.py
tests/utils.py
tests/test_generated_fixtures.py
```

Streamlit UI는 별도 패키지에서 실행합니다. 라이브러리는 Streamlit에 의존하지 않고,
UI는 설치된 `krairport` 패키지를 import해서 `KrairportClient.debug()`를 호출합니다.

## DebugRun

`KrairportClient.debug(function_name, **input_data)`와 `debug_*` 편의 메서드는 `DebugRun`을
반환합니다.

```python
from krairport import KrairportClient

client = KrairportClient.from_env()
run = client.debug_departures(
    airport_code="GMP",
    searchday="20260430",
    from_time="0600",
    to_time="1200",
)
```

`DebugRun` 필드:

- `function`: 실행한 public 함수 이름
- `input`: UI 입력값
- `request`: fixture 저장용 요청 메타데이터
- `response`: replay에 사용할 raw body 후보
- `parsed`: Pydantic 모델 또는 모델 목록
- `processed`: 비교 대상 결과
- `trace`: UI 표시용 실행 흔적
- `error`: 예외가 발생한 경우 예외 타입과 메시지

`response.body`는 public 모델의 `raw` 필드를 기반으로 구성합니다. 외부 API 인증값은
저장 전에 `redact_sensitive()`를 통과해 `<REDACTED>`로 마스킹합니다.

## API 카탈로그

`api_catalog(function_name=None, provider=None)`는 라이브러리가 지원하는 공공데이터
endpoint 목록을 반환합니다. 각 항목은 provider, 사람이 읽기 쉬운 `dataset_name`,
service, operation, endpoint, response format, 서비스키 신청 링크(`service_key_url`)를
포함합니다.

```python
from krairport import api_catalog

for item in api_catalog("parking_status"):
    print(item.dataset_name, item.service_key_url)
```

Debug UI는 선택한 함수의 카탈로그 항목을 Debug Trace 탭에 표로 표시하고, sidebar에는
해당 API의 공공데이터포털 활용신청 링크를 함께 보여줍니다.

## fixture 포맷

```json
{
  "name": "debug_kac_departure",
  "function": "departures",
  "description": "KAC departure fixture replay sample",
  "input": {"airport_code": "GMP"},
  "request": {"function": "departures", "params": {"airport_code": "GMP"}},
  "response": {"status_code": 200, "headers": {}, "body": []},
  "parsed": [],
  "processed": [],
  "assertion": {
    "mode": "snapshot",
    "exclude_fields": ["fetched_at", "request_id", "updated_at"],
    "required_fields": []
  },
  "meta": {
    "created_at": "2026-05-15T20:30:00+09:00",
    "library_version": "0.1.0",
    "source": "debug_ui"
  }
}
```

fixture 저장 위치는 `tests/fixtures/{function}/{case}.json`입니다. 같은 파일명은
기본적으로 덮어쓰지 않습니다.

## assertion mode

| mode | 의미 |
|---|---|
| `snapshot` | `processed` 전체를 비교하고 `exclude_fields`를 재귀적으로 제외합니다. |
| `schema_only` | parser/processor가 예외 없이 결과를 만들면 통과합니다. |
| `required_fields` | `required_fields`에 적은 필드가 결과에 존재하는지 확인합니다. |
| `count` | list 길이 또는 `count` 값을 비교합니다. |

## pytest replay

`tests/test_generated_fixtures.py`는 `tests/fixtures/*/*.json`을 자동으로 읽습니다.
테스트는 외부 API를 호출하지 않고 저장된 `response.body`를 `tests/runners.py`의 parser에
다시 넣은 뒤 `processed` 기대값과 비교합니다.

```powershell
python -m pytest tests/test_generated_fixtures.py
```

새 public 함수가 fixture 저장 대상이 되면 `tests/runners.py`의 `RUNNERS`에 parser와
processor를 추가해야 합니다.
