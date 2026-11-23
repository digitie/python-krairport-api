from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@dataclass(frozen=True)
class RecordedCall:
    url: str
    params: Mapping[str, Any]
    timeout: float


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        json_data: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self._json_data = json_data
        self.headers = dict(headers or {})

    def json(self) -> Any:
        if self._json_data is None:
            raise ValueError("no JSON payload")
        return self._json_data


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[RecordedCall] = []

    async def get(self, url: str, *, params: Mapping[str, Any], timeout: float) -> FakeResponse:
        self.calls.append(RecordedCall(url=url, params=dict(params), timeout=timeout))
        if not self._responses:
            raise AssertionError("FakeSession has no response left")
        return self._responses.pop(0)


class AsyncFakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[RecordedCall] = []

    async def get(self, url: str, *, params: Mapping[str, Any], timeout: float) -> FakeResponse:
        self.calls.append(RecordedCall(url=url, params=dict(params), timeout=timeout))
        if not self._responses:
            raise AssertionError("AsyncFakeSession has no response left")
        return self._responses.pop(0)

    async def aclose(self) -> None:
        return None


@pytest.fixture(autouse=True)
def retry_sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """재시도 backoff를 실제로 기다리지 않고 요청한 대기 시간만 기록한다."""
    import krairport._http as http_module

    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(http_module, "_sleep", fake_sleep)
    return sleeps


@pytest.fixture
def load_fixture() -> Any:
    def _load(name: str) -> str:
        return (FIXTURE_DIR / name).read_text(encoding="utf-8")

    return _load
