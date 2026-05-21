"""krairport 클라이언트 런타임 설정."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 3
DATA_GO_KR_SERVICE_KEY = "DATA_GO_KR_SERVICE_KEY"


@dataclass(frozen=True, slots=True)
class KrairportConfig:
    """명시 인자, 환경변수, 로컬 `.env` 파일에서 읽은 런타임 설정."""

    kac_service_key: str | None = None
    iiac_service_key: str | None = None
    timeout: float = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES

    @classmethod
    def from_env(
        cls,
        *,
        kac_service_key: str | None = None,
        iiac_service_key: str | None = None,
        service_key_name: str = DATA_GO_KR_SERVICE_KEY,
        env_file: str | Path | None = None,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> KrairportConfig:
        file_values = _load_env_files(env_file)
        env_service_key = _env_value(service_key_name, file_values)
        return cls(
            kac_service_key=_clean(kac_service_key) or env_service_key,
            iiac_service_key=_clean(iiac_service_key) or env_service_key,
            timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
            retries=retries if retries is not None else DEFAULT_RETRIES,
        )


def _env_value(name: str, file_values: dict[str, str]) -> str | None:
    value = _clean(os.getenv(name))
    if value is not None:
        return value
    value = _clean(file_values.get(name))
    if value is not None:
        return value
    return None


def _load_env_files(env_file: str | Path | None) -> dict[str, str]:
    paths = [Path(env_file)] if env_file is not None else _default_env_paths()
    values: dict[str, str] = {}
    for path in paths:
        resolved = path.expanduser()
        if resolved.exists() and resolved.is_file():
            values.update(_read_dotenv(resolved))
    return values


def _default_env_paths() -> list[Path]:
    cwd = Path.cwd().resolve()
    paths: list[Path] = []
    for directory in (cwd, *cwd.parents):
        for filename in (".env", ".env.local"):
            path = directory / filename
            if path not in paths:
                paths.append(path)
    return paths


def _read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        cleaned = _clean(_strip_quotes(raw_value.strip()))
        if cleaned is not None:
            values[key.strip().lstrip("\ufeff")] = cleaned
    return values


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
