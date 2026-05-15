"""Streamlit 디버그 UI에서 pytest replay fixture를 저장하는 도구."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from krairport import __version__
from krairport.debug import jsonable, redact_sensitive

DEFAULT_ASSERTION = {
    "mode": "snapshot",
    "exclude_fields": ["fetched_at", "request_id", "updated_at"],
    "required_fields": [],
}
_SAFE_FILENAME = re.compile(r"[^0-9A-Za-z가-힣._-]+")


def slugify(value: str) -> str:
    """사람이 입력한 case name을 fixture 파일명으로 사용할 수 있게 정리합니다."""

    text = _SAFE_FILENAME.sub("-", value.strip().lower())
    text = re.sub(r"-{2,}", "-", text).strip("-._")
    if not text:
        raise ValueError("case_name must contain at least one safe filename character")
    return text


def build_fixture(
    *,
    function_name: str,
    case_name: str,
    description: str,
    input_data: dict[str, Any],
    request_data: dict[str, Any],
    response_data: dict[str, Any],
    parsed_result: Any,
    processed_result: Any,
    assertion: dict[str, Any] | None = None,
    library_version: str | None = None,
) -> dict[str, Any]:
    """저장 전 미리보기와 파일 저장이 공유하는 fixture dict를 만듭니다."""

    safe_case_name = slugify(case_name)
    return {
        "name": safe_case_name,
        "function": function_name,
        "description": description,
        "input": redact_sensitive(jsonable(input_data)),
        "request": redact_sensitive(jsonable(request_data)),
        "response": redact_sensitive(jsonable(response_data)),
        "parsed": redact_sensitive(jsonable(parsed_result)),
        "processed": redact_sensitive(jsonable(processed_result)),
        "assertion": assertion or DEFAULT_ASSERTION,
        "meta": {
            "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "library_version": library_version or __version__,
            "source": "debug_ui",
        },
    }


def save_fixture(
    *,
    base_dir: str | Path,
    function_name: str,
    case_name: str,
    description: str,
    input_data: dict[str, Any],
    request_data: dict[str, Any],
    response_data: dict[str, Any],
    parsed_result: Any,
    processed_result: Any,
    assertion: dict[str, Any] | None = None,
    library_version: str | None = None,
    overwrite: bool = False,
) -> Path:
    """`tests/fixtures/{function}/{case}.json` 형태로 replay fixture를 저장합니다."""

    fixture = build_fixture(
        function_name=function_name,
        case_name=case_name,
        description=description,
        input_data=input_data,
        request_data=request_data,
        response_data=response_data,
        parsed_result=parsed_result,
        processed_result=processed_result,
        assertion=assertion,
        library_version=library_version,
    )
    fixture_dir = Path(base_dir) / function_name
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixture_dir / f"{fixture['name']}.json"

    if fixture_path.exists() and not overwrite:
        raise FileExistsError(f"Fixture already exists: {fixture_path}")

    with fixture_path.open("w", encoding="utf-8") as file:
        json.dump(fixture, file, ensure_ascii=False, indent=2)
        file.write("\n")

    return fixture_path
