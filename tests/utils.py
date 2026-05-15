from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def remove_fields(obj: Any, exclude_fields: list[str]) -> Any:
    if isinstance(obj, Mapping):
        return {
            key: remove_fields(value, exclude_fields)
            for key, value in obj.items()
            if str(key) not in exclude_fields
        }
    if isinstance(obj, list):
        return [remove_fields(value, exclude_fields) for value in obj]
    return obj


def assert_case(actual: Any, expected: Any, assertion: Mapping[str, Any]) -> None:
    mode = assertion.get("mode", "snapshot")

    if mode == "snapshot":
        exclude_fields = _string_list(assertion.get("exclude_fields", []))
        assert remove_fields(actual, exclude_fields) == remove_fields(expected, exclude_fields)
    elif mode == "required_fields":
        for field in _string_list(assertion.get("required_fields", [])):
            assert _contains_field(actual, field)
    elif mode == "schema_only":
        assert actual is not None
    elif mode == "count":
        assert _count(actual) == _count(expected)
    else:
        raise ValueError(f"Unknown assertion mode: {mode}")


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _contains_field(obj: Any, dotted_field: str) -> bool:
    if isinstance(obj, list):
        return all(_contains_field(item, dotted_field) for item in obj)
    current = obj
    for part in dotted_field.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False
        current = current[part]
    return True


def _count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, Mapping) and "count" in value:
        return int(value["count"])
    return 1
