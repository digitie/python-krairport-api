"""디버그 UI와 fixture 생성을 위한 실행 결과 구조."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from typing import Any, cast

from pydantic import BaseModel

DEBUGGABLE_FUNCTIONS = frozenset(
    {
        "departures",
        "arrivals",
        "aircraft_assignments",
        "parking_fees",
        "parking_status",
        "arrival_congestion",
        "passenger_forecast",
        "airport_codes",
        "flight_schedules",
        "airport_facilities",
        "bus_routes",
        "taxi_status",
        "world_weather",
        "service_destinations",
        "kac_raw_items",
        "iiac_raw_items",
    }
)

SENSITIVE_KEYS = {
    "authorization",
    "x-api-key",
    "api_key",
    "apikey",
    "servicekey",
    "service_key",
    "access_token",
    "refresh_token",
}


@dataclass(frozen=True)
class DebugRun:
    """UI가 raw/parsed/processed/error를 분리해서 보여줄 수 있는 실행 결과."""

    function: str
    input: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any]
    parsed: Any
    processed: Any
    trace: list[str]
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """fixture 저장과 UI 표시가 가능한 JSON 호환 dict로 변환합니다."""

        return cast(dict[str, Any], jsonable(self))


def debug_call(client: Any, function_name: str, **input_data: Any) -> DebugRun:
    """`KrairportClient` public 함수를 실행하고 fixture 후보 데이터를 묶습니다."""

    trace = [f"selected function: {function_name}"]
    safe_input = redact_sensitive(jsonable(input_data))
    request = {
        "function": function_name,
        "params": safe_input,
    }

    if function_name not in DEBUGGABLE_FUNCTIONS:
        error = {
            "type": "ValueError",
            "message": f"debug fixture generation is not supported for {function_name!r}",
        }
        return DebugRun(
            function=function_name,
            input=safe_input,
            request=request,
            response={},
            parsed=None,
            processed=None,
            trace=trace + ["rejected unsupported function"],
            error=error,
        )

    try:
        target = getattr(client, function_name)
        trace.append(f"calling KrairportClient.{function_name}()")
        processed = target(**input_data)
        response_body = _raw_body_from_processed(processed)
        trace.append("captured raw rows from public model.raw fields")
        return DebugRun(
            function=function_name,
            input=safe_input,
            request=request,
            response={
                "status_code": None,
                "headers": {},
                "body": redact_sensitive(response_body),
            },
            parsed=processed,
            processed=processed,
            trace=trace,
        )
    except Exception as exc:
        trace.append(f"raised {type(exc).__name__}")
        return DebugRun(
            function=function_name,
            input=safe_input,
            request=request,
            response={},
            parsed=None,
            processed=None,
            trace=trace,
            error=_error_to_dict(exc),
        )


def jsonable(obj: Any) -> Any:
    """Pydantic v2 모델과 dataclass를 JSON 저장 가능한 값으로 변환합니다."""

    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if is_dataclass(obj) and not isinstance(obj, type):
        return {key: jsonable(value) for key, value in asdict(obj).items()}
    if isinstance(obj, Mapping):
        return {str(key): jsonable(value) for key, value in obj.items()}
    if isinstance(obj, list | tuple | set):
        return [jsonable(value) for value in obj]
    return obj


def redact_sensitive(obj: Any) -> Any:
    """fixture에 저장되면 안 되는 인증 관련 값을 재귀적으로 마스킹합니다."""

    if isinstance(obj, Mapping):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            key_text = str(key)
            if key_text.lower() in SENSITIVE_KEYS:
                result[key_text] = "<REDACTED>"
            else:
                result[key_text] = redact_sensitive(value)
        return result
    if isinstance(obj, list | tuple | set):
        return [redact_sensitive(value) for value in obj]
    return obj


def _raw_body_from_processed(processed: Any) -> Any:
    if isinstance(processed, list):
        return [_raw_body_from_processed(item) for item in processed]
    raw = getattr(processed, "raw", None)
    if raw is not None:
        return jsonable(raw)
    return jsonable(processed)


def _error_to_dict(exc: Exception) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
    }
