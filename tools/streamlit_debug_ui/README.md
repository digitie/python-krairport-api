# krairport-debug-ui

`krairport` 실행 결과를 빠르게 확인하고, 의미 있는 케이스를
`python-krairport-api/tests/fixtures/{function}/{case}.json` replay fixture로 저장하는
Streamlit UI입니다.

## 실행

```powershell
cd tools\streamlit_debug_ui
pip install -e .
streamlit run app.py
```

`.env`에 저장된 키는 sidebar 기본값으로 자동 로드됩니다.

```dotenv
KAC_SERVICE_KEY=...
IIAC_SERVICE_KEY=...
```

복사/붙여넣기 중 앞뒤에 들어간 공백과 줄바꿈은 요청 전에 제거됩니다.

Function을 선택하면 sidebar에 해당 API의 공공데이터포털 서비스키 신청 링크가 표시되고,
Debug Trace 탭에는 데이터셋명, service, operation, endpoint, 신청 링크가 표로 표시됩니다.

개발 중에는 라이브러리 저장소를 editable로 먼저 설치할 수 있습니다.

```powershell
pip install -e ..\..
pip install -e .
streamlit run app.py
```

## 저장 포맷

- `input`, `request`, `response`, `parsed`, `processed`, `assertion`, `meta`를 저장합니다.
- `serviceKey`, `Authorization`, `api_key`, access/refresh token 계열 값은 저장 전에 `<REDACTED>`로 마스킹합니다.
- 같은 fixture 이름은 기본적으로 덮어쓰지 않습니다.
- pytest replay는 실제 외부 API를 호출하지 않고 저장된 `response.body`를 parser/processor에 다시 넣습니다.

## 검증

```powershell
pytest
```
