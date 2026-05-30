# CLAUDE.md — 프로젝트 컨텍스트

이 파일은 Claude Code를 비롯한 AI 에이전트가 세션 시작 시 컨텍스트를 파악할 수 있도록 자동으로 참고하는 문서입니다.
프로젝트 구현 가이드는 `AGENTS.md`에, 구현 불변 조건과 체크리스트는 `SKILL.md`에, API 명세 및 세부 규칙은 `krairport-api.md`에 정리되어 있습니다.

## 프로젝트 현황 (2026-05-31)

한국공항공사(KAC)와 인천국제공항공사(IIAC) 공항 OpenAPI를 단일 인터페이스로 통합하는 비공식 Python 클라이언트(`krairport`) 프로젝트입니다.

- **라우팅 규칙**: `ICN`은 IIAC로, 그 외 국내 공항은 KAC로 라우팅합니다. 잘못된 조합은 `UnsupportedAirportError`를 발생시킵니다.
- **아키텍처**: Pydantic v2 기반의 frozen immutable 응답 모델 및 `StrEnum`을 준수하며, `httpx`를 핵심 HTTP 클라이언트로 사용합니다.
- **좌표/주소**: `krairport.Coordinate`를 좌표 정규화 및 DMS 파싱에 사용하고, 주소는 provider 명시값이 있을 때만 보존합니다.
- **테스트 및 검증**: 오프라인 테스트를 원칙으로 하며, 실제 API 호출(live test)은 opt-in 마커로 격리되어 있습니다.

## 에이전트 worktree + CodeGraph

ChatGPT Codex는 `F:\dev\python-krairport-api-codex`, Claude Code는 `F:\dev\python-krairport-api-claude`, Google Antigravity 2.0은 `F:\dev\python-krairport-api-antigravity`를 고정 worktree로 사용합니다.

- **브랜치 규칙**: 각 worktree에서는 `git fetch origin` 후 `git switch -c agent/<topic> main`으로 전용 피처 브랜치를 분기하여 작업합니다.
- **CodeGraph**: 각 worktree 생성 시 최초 1회 `codegraph init -i`를 수행하여 인덱스를 초기화하고, 이후 코드 탐색을 위해 `codegraph sync`를 활용합니다. `.codegraph/`는 gitignore 대상입니다.

## 빠른 검증 명령

```bash
# 가상환경 활성화 후 개발용 의존성 설치
pip install -e .[dev]

# 품질 게이트 (PR 전 로컬에서 반드시 검증합니다)
python -m compileall src/krairport tests    # 컴파일 검사
python -m ruff check .                       # Ruff 스타일 린트
python -m mypy src/krairport                 # Mypy 정적 타입 검사
python -m pytest                             # Pytest 단위 테스트 실행
python -m pytest --cov=krairport --cov-fail-under=85  # 테스트 커버리지 검증
```

## 작업 후 의무사항

1. `python -m ruff check .` 및 `python -m mypy src/krairport` 정적 검증 통과
2. `python -m pytest` 단위 테스트 통과 (커버리지 85% 이상 확인)
3. 새로운 실수 패턴 발견 시 `docs/repeated-mistakes.md` 및 `SKILL.md` 업데이트
4. 사용자 가시 변경이 있을 경우 `CHANGELOG.md` 갱신
5. public API 계약 변경 시 `README.md` 및 `krairport-api.md` 동기화
