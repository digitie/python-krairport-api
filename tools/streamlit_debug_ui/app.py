from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from krairport import KrairportClient, __version__, api_catalog
from krairport.catalog import ApiCatalogItem
from krairport.debug import DEBUGGABLE_FUNCTIONS, DebugRun, jsonable
from pydantic import BaseModel

from fixture_writer import build_fixture, save_fixture

ENV_KEY_NAMES = ("KAC_SERVICE_KEY", "IIAC_SERVICE_KEY")
SECRET_PARAM_NAMES = {
    "serviceKey",
    "ServiceKey",
    "service_key",
    "KAC_SERVICE_KEY",
    "IIAC_SERVICE_KEY",
}

FIELD_SPECS: dict[str, list[tuple[str, str, Any]]] = {
    "departures": [
        ("airport_code", "text", "ICN"),
        ("searchday", "text", ""),
        ("from_time", "text", ""),
        ("to_time", "text", ""),
        ("flight_id", "text", ""),
        ("flight_unique_id", "text", ""),
        ("airline_code", "text", ""),
        ("line", "text", ""),
        ("counterpart_airport_code", "text", ""),
        ("lang", "text", "K"),
        ("use_detailed", "optional_bool", None),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 10),
    ],
    "arrivals": [
        ("airport_code", "text", "ICN"),
        ("searchday", "text", ""),
        ("from_time", "text", ""),
        ("to_time", "text", ""),
        ("flight_id", "text", ""),
        ("flight_unique_id", "text", ""),
        ("airline_code", "text", ""),
        ("line", "text", ""),
        ("counterpart_airport_code", "text", ""),
        ("lang", "text", "K"),
        ("use_detailed", "optional_bool", None),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 10),
    ],
    "aircraft_assignments": [
        ("airport_code", "text", "CJU"),
        ("sch_st_time", "text", ""),
        ("sch_ed_time", "text", ""),
        ("flight_id", "text", ""),
        ("flight_unique_id", "text", ""),
        ("aircraft_registration", "text", ""),
        ("aircraft_type", "text", ""),
        ("line", "text", ""),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 10),
    ],
    "parking_fees": [("airport_code", "text", "GMP")],
    "parking_status": [
        ("airport_code", "text", "ICN"),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
    "arrival_congestion": [
        ("airport_code", "text", "ICN"),
        ("terminal", "text", ""),
        ("airport", "text", ""),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
    "passenger_forecast": [
        ("airport_code", "text", "ICN"),
        ("selectdate", "int", 0),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
    "flight_schedules": [
        ("airport_code", "text", "ICN"),
        ("direction", "select", "arrival"),
        ("counterpart_airport_code", "text", ""),
        ("sch_date", "text", ""),
        ("airline_code", "text", ""),
        ("flight_id", "text", ""),
        ("international", "bool", False),
        ("lang", "text", "K"),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
    "airport_facilities": [
        ("airport_code", "text", "ICN"),
        ("facility_name", "text", ""),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
    "bus_routes": [
        ("airport_code", "text", "ICN"),
        ("area", "text", "1"),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
    "taxi_status": [
        ("airport_code", "text", "ICN"),
        ("terminal", "text", ""),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
    "world_weather": [
        ("airport_code", "text", "ICN"),
        ("direction", "select", "arrival"),
        ("from_time", "text", ""),
        ("to_time", "text", ""),
        ("airport", "text", ""),
        ("flight_id", "text", ""),
        ("airline_code", "text", ""),
        ("lang", "text", "K"),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
    "service_destinations": [
        ("airport_code", "text", ""),
        ("lang", "text", "K"),
        ("page_no", "int", 1),
        ("num_of_rows", "int", 100),
    ],
}

FUNCTION_LABELS = {
    "departures": "Departures",
    "arrivals": "Arrivals",
    "aircraft_assignments": "Aircraft assignments",
    "parking_fees": "Parking fees",
    "parking_status": "Parking status",
    "arrival_congestion": "Arrival congestion",
    "passenger_forecast": "Passenger forecast",
    "flight_schedules": "Flight schedules",
    "airport_facilities": "Airport facilities",
    "bus_routes": "Bus routes",
    "taxi_status": "Taxi status",
    "world_weather": "World weather",
    "service_destinations": "Service destinations",
}

REQUIRED_FIELDS = {
    "departures": {"airport_code"},
    "arrivals": {"airport_code"},
    "flight_schedules": {"airport_code", "direction"},
    "bus_routes": {"airport_code", "area"},
    "world_weather": {"airport_code", "direction"},
}


def main() -> None:
    st.set_page_config(page_title="Krairport Debug UI", layout="wide")
    st.title("Krairport Debug UI")

    function_names = sorted(name for name in DEBUGGABLE_FUNCTIONS if name in FIELD_SPECS)
    function_name = st.sidebar.selectbox(
        "API",
        function_names,
        format_func=_function_label,
    )
    catalog_items = api_catalog(function_name)
    st.sidebar.caption("API full name")
    st.sidebar.write(_api_full_name(function_name, catalog_items))
    st.sidebar.caption(_api_description(catalog_items))

    env_defaults = _load_local_env()
    env_sources = _env_key_sources(env_defaults)
    st.sidebar.subheader("Environment")
    environment_options = ["env", "manual"] if env_sources else ["manual", "env"]
    environment = st.sidebar.selectbox("Environment", environment_options)
    if environment == "env":
        if env_sources:
            st.sidebar.caption(
                f"{env_sources[0]['name']} value will be used. Source: {env_sources[0]['source']}"
            )
        else:
            st.sidebar.warning("No KAC_SERVICE_KEY or IIAC_SERVICE_KEY found in env files.")

    st.sidebar.subheader("Auth")
    if environment == "manual":
        kac_key = st.sidebar.text_input(
            "KAC service key",
            value=env_defaults.get("KAC_SERVICE_KEY", ""),
            type="password",
            placeholder="Manual input",
            help="Available env name: KAC_SERVICE_KEY",
        )
        iiac_key = st.sidebar.text_input(
            "IIAC service key",
            value=env_defaults.get("IIAC_SERVICE_KEY", ""),
            type="password",
            placeholder="Manual input",
            help="Available env name: IIAC_SERVICE_KEY",
        )
    else:
        kac_key = env_defaults.get("KAC_SERVICE_KEY", "")
        iiac_key = env_defaults.get("IIAC_SERVICE_KEY", "")

    _service_key_links(function_name)
    timeout = st.sidebar.number_input(
        "Timeout",
        min_value=1.0,
        max_value=120.0,
        value=10.0,
        step=1.0,
        help="API request timeout in seconds.",
    )
    fixture_base_dir = _fixture_base_dir_sidebar()

    tabs = st.tabs(
        [
            "Raw Response",
            "Pydantic Model",
            "Processed Result",
            "Validation Errors",
            "Debug Trace",
            "Fixture / Testcase",
        ]
    )

    with tabs[0]:
        _raw_response_tab(function_name, kac_key, iiac_key, float(timeout))
    with tabs[1]:
        _pydantic_model_tab(function_name)
    with tabs[2]:
        _processed_result_tab(function_name)
    with tabs[3]:
        _validation_errors_tab(function_name)
    with tabs[4]:
        _debug_trace_tab(function_name, function_names)
    with tabs[5]:
        _fixture_tab(function_name, fixture_base_dir)


def _raw_response_tab(
    function_name: str,
    kac_key: str | None,
    iiac_key: str | None,
    timeout: float,
) -> None:
    catalog_items = api_catalog(function_name)
    st.subheader(_dataset_heading(function_name, catalog_items))
    st.caption(_api_full_name(function_name, catalog_items))

    try:
        submitted, input_data, extra_params, missing = _request_form(function_name)
    except ValueError as exc:
        st.error(str(exc))
        return

    preview = {**input_data, **extra_params}
    st.subheader("Request params preview")
    st.json(preview)

    if not submitted:
        run = _current_run(function_name)
        if run is not None:
            _show_json(run.response)
        return
    if missing:
        st.error("Required parameters are missing: " + ", ".join(missing))
        return

    async def fetch() -> DebugRun:
        async with _client(kac_key, iiac_key, timeout) as client:
            return await client.debug(function_name, **preview)

    run = asyncio.run(fetch())
    _store_run(function_name, run)
    _show_json(run.response)


def _request_form(function_name: str) -> tuple[bool, dict[str, Any], dict[str, Any], list[str]]:
    specs = FIELD_SPECS[function_name]
    required_names = REQUIRED_FIELDS.get(function_name, set())
    required_specs = [spec for spec in specs if spec[0] in required_names]
    optional_specs = [spec for spec in specs if spec[0] not in required_names]
    key_prefix = f"request-form:{function_name}"

    with st.form(key_prefix):
        st.subheader("Required parameters")
        if required_specs:
            required_values = _render_input_grid(required_specs, key_prefix=key_prefix)
        else:
            st.caption("No required parameters are defined for this API.")
            required_values = {}

        st.subheader("Optional parameters")
        optional_values = _render_input_grid(optional_specs, key_prefix=key_prefix)
        extra_text = st.text_area(
            "Extra params JSON",
            value="{}",
            height=110,
            help="Add provider-specific kwargs that are not shown in the form.",
            key=f"{key_prefix}:extra",
        )
        submitted = st.form_submit_button("Run selected API")

    params = {**required_values, **optional_values}
    missing = [name for name in required_names if name not in params]
    extra_params = _parse_extra_params(extra_text)
    return submitted, params, extra_params, missing


def _render_input_grid(
    specs: list[tuple[str, str, Any]],
    *,
    key_prefix: str,
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for index in range(0, len(specs), 2):
        columns = st.columns(2)
        for column, spec in zip(columns, specs[index : index + 2], strict=False):
            name, kind, default = spec
            with column:
                value = _field(name, kind, default, key=f"{key_prefix}:param:{name}")
            if value is not None:
                values[name] = value
    return values


def _field(name: str, kind: str, default: Any, *, key: str) -> Any:
    if kind == "int":
        return int(st.number_input(name, value=int(default), step=1, key=key))
    if kind == "bool":
        return st.checkbox(name, value=bool(default), key=key)
    if kind == "optional_bool":
        selected = st.selectbox(name, ["auto", "true", "false"], key=key)
        return {"auto": None, "true": True, "false": False}[selected]
    if kind == "select":
        return st.selectbox(
            name,
            ["arrival", "departure"],
            index=0 if default == "arrival" else 1,
            key=key,
        )
    value = st.text_input(name, value=str(default), key=key)
    return value.strip() or None


def _parse_extra_params(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Extra params JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Extra params JSON must be an object")
    return {key: value for key, value in payload.items() if key not in SECRET_PARAM_NAMES}


def _client(
    kac_key: str | None,
    iiac_key: str | None,
    timeout: float,
) -> KrairportClient:
    return KrairportClient(
        kac_service_key=_clean_secret(kac_key),
        iiac_service_key=_clean_secret(iiac_key),
        timeout=timeout,
    )


def _pydantic_model_tab(function_name: str) -> None:
    run = _current_run(function_name)
    if run is None:
        st.info("Run the selected API in the Raw Response tab to inspect Pydantic models here.")
        return
    if run.error:
        st.warning("The last run has an error. Check the Validation Errors tab.")
        return
    _show_result(run.parsed)


def _processed_result_tab(function_name: str) -> None:
    run = _current_run(function_name)
    if run is None:
        st.info("Run the selected API in the Raw Response tab to display processed rows.")
        return
    if run.error:
        st.warning("The last run has an error. Check the Validation Errors tab.")
        return
    _show_result(run.processed)


def _validation_errors_tab(function_name: str) -> None:
    run = _current_run(function_name)
    if run is None:
        st.info("No API has been run for the current selection.")
        return
    if not run.error:
        st.success("No validation or request error in the current run.")
        return
    _show_json(run.error)


def _debug_trace_tab(function_name: str, function_names: Iterable[str]) -> None:
    run = _current_run(function_name)
    if run is None:
        st.info("Run the selected API in the Raw Response tab to collect a debug trace.")
    else:
        _show_json(run.trace)

    rows = [row for name in function_names for row in _catalog_rows(name)]
    st.subheader("Catalog")
    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                "function": st.column_config.TextColumn("Function"),
                "provider": st.column_config.TextColumn("Provider"),
                "dataset_name": st.column_config.TextColumn("Dataset"),
                "service": st.column_config.TextColumn("Service"),
                "operation": st.column_config.TextColumn("Operation"),
                "response_format": st.column_config.TextColumn("Format"),
                "service_key_url": st.column_config.LinkColumn("Service key link"),
                "endpoint": st.column_config.LinkColumn("Endpoint"),
                "notes": st.column_config.TextColumn("Notes"),
            },
        )

    st.subheader("Selected API")
    selected_rows = _catalog_rows(function_name)
    if selected_rows:
        st.json(selected_rows)
        for item in api_catalog(function_name):
            st.link_button(f"{str(item.provider).upper()} service key", item.service_key_url)
    else:
        st.info("No catalog entries for this API.")
    st.caption(f"credential env: {', '.join(ENV_KEY_NAMES)}")


def _fixture_tab(function_name: str, fixture_base_dir: str) -> None:
    run = _current_run(function_name)
    st.caption("Fixture base dir")
    st.code(fixture_base_dir, language=None)
    if run is None:
        st.info("Run the selected API in the Raw Response tab to save a replay fixture.")
        return
    if run.error is not None:
        st.warning("Only successful runs can be saved as fixtures.")
        return
    _fixture_panel(run, function_name, fixture_base_dir)


def _show_result(result: Any) -> None:
    data = jsonable(result)
    _show_json(data)
    if isinstance(result, list) and result and isinstance(result[0], BaseModel):
        rows = [item.model_dump(mode="json") for item in result]
        st.dataframe(pd.json_normalize(rows, sep="."), use_container_width=True)


def _show_json(value: Any) -> None:
    data = jsonable(value)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        data = {"value": data}
    st.json(data)


def _service_key_links(function_name: str) -> None:
    items = api_catalog(function_name)
    if not items:
        return
    st.sidebar.caption("Service key links")
    for item in items:
        st.sidebar.link_button(
            f"{str(item.provider).upper()} - {item.dataset_name}",
            item.service_key_url,
            use_container_width=True,
        )


def _fixture_base_dir_sidebar() -> str:
    st.sidebar.subheader("Fixtures")
    candidates = _fixture_dir_candidates()
    options = [str(path) for path in candidates]
    custom_label = "Custom..."
    selected = st.sidebar.selectbox("Fixture base dir", [*options, custom_label])
    if selected == custom_label:
        selected = st.sidebar.text_input(
            "Custom fixture base dir",
            value=str((_repo_root() / "tests" / "fixtures").resolve()),
        )
    st.sidebar.caption(selected)
    return selected


def _fixture_dir_candidates() -> list[Path]:
    preferred = [
        _repo_root() / "tests" / "fixtures",
        _repo_root() / "tests",
        _repo_root() / "tools",
        _repo_root(),
    ]
    candidates: list[Path] = []
    for path in preferred:
        resolved = path.resolve()
        if resolved not in candidates:
            candidates.append(resolved)
    return candidates


def _catalog_rows(function_name: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in api_catalog(function_name):
        rows.append(_catalog_item_row(item))
    return rows


def _catalog_item_row(item: ApiCatalogItem) -> dict[str, str]:
    return {
        "function": item.function,
        "provider": str(item.provider),
        "dataset_name": item.dataset_name,
        "service": item.service,
        "operation": item.operation,
        "response_format": item.response_format,
        "service_key_url": item.service_key_url,
        "endpoint": item.endpoint,
        "notes": item.notes,
    }


def _fixture_panel(run: DebugRun, function_name: str, fixture_base_dir: str) -> None:
    with st.expander("Save as fixture", expanded=True):
        case_name = st.text_input("Case name")
        description = st.text_area("Description")
        assertion_mode = st.selectbox(
            "Assertion mode",
            ["snapshot", "schema_only", "required_fields", "count"],
        )
        exclude_fields_raw = st.text_input(
            "Exclude fields",
            value="fetched_at, request_id, updated_at",
        )
        required_fields_raw = st.text_input("Required fields", value="")
        overwrite = st.checkbox("Overwrite existing fixture", value=False)

        assertion = {
            "mode": assertion_mode,
            "exclude_fields": _csv(exclude_fields_raw),
            "required_fields": _csv(required_fields_raw),
        }
        if case_name:
            preview = build_fixture(
                function_name=function_name,
                case_name=case_name,
                description=description,
                input_data=run.input,
                request_data=run.request,
                response_data=run.response,
                parsed_result=run.parsed,
                processed_result=run.processed,
                assertion=assertion,
                library_version=__version__,
            )
            st.json(preview)

        if st.button("Save as fixture", disabled=not case_name):
            path = save_fixture(
                base_dir=fixture_base_dir,
                function_name=function_name,
                case_name=case_name,
                description=description,
                input_data=run.input,
                request_data=run.request,
                response_data=run.response,
                parsed_result=run.parsed,
                processed_result=run.processed,
                assertion=assertion,
                library_version=__version__,
                overwrite=overwrite,
            )
            st.success(f"Saved: {path}")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _store_run(function_name: str, run: DebugRun) -> None:
    st.session_state["last_run"] = {
        "function": function_name,
        "run": run,
    }


def _current_run(function_name: str) -> DebugRun | None:
    stored = st.session_state.get("last_run")
    if not isinstance(stored, dict) or stored.get("function") != function_name:
        return None
    run = stored.get("run")
    return run if isinstance(run, DebugRun) else None


def _function_label(function_name: str) -> str:
    return FUNCTION_LABELS.get(function_name, function_name.replace("_", " ").title())


def _api_full_name(function_name: str, items: tuple[ApiCatalogItem, ...]) -> str:
    if not items:
        return _function_label(function_name)
    parts = []
    for item in items:
        parts.append(f"{str(item.provider).upper()} / {item.service} / {item.operation}")
    return " | ".join(parts)


def _api_description(items: tuple[ApiCatalogItem, ...]) -> str:
    if not items:
        return "No catalog entry is available for this API."
    datasets = " / ".join(dict.fromkeys(item.dataset_name for item in items))
    notes = " ".join(item.notes for item in items if item.notes)
    return f"{datasets} {notes}".strip()


def _dataset_heading(function_name: str, items: tuple[ApiCatalogItem, ...]) -> str:
    if not items:
        return _function_label(function_name)
    return " / ".join(dict.fromkeys(item.dataset_name for item in items))


def _env_key_sources(values: dict[str, str]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for key in ENV_KEY_NAMES:
        env_value = os.getenv(key)
        if env_value is not None and env_value.strip():
            sources.append({"name": key, "source": "process env"})
            return sources
    for key in ENV_KEY_NAMES:
        if values.get(key):
            sources.append({"name": key, "source": ".env"})
            return sources
    return sources


def _load_local_env(paths: list[Path] | None = None) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths or _default_env_paths():
        if path.exists():
            values.update(_read_dotenv(path))
    for key in ENV_KEY_NAMES:
        value = os.getenv(key)
        cleaned = _clean_secret(value)
        if cleaned is not None:
            values[key] = cleaned
    return values


def _default_env_paths() -> list[Path]:
    app_dir = Path(__file__).resolve().parent
    dirs = [
        _repo_root().parent / "pykrairport",
        *reversed(app_dir.parents),
        app_dir,
        Path.cwd(),
    ]
    paths: list[Path] = []
    for directory in dirs:
        for filename in (".env", ".env.local"):
            path = (directory / filename).resolve()
            if path not in paths:
                paths.append(path)
    return paths


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
        key = key.strip().lstrip("\ufeff")
        if key not in ENV_KEY_NAMES:
            continue
        value = _strip_quotes(raw_value.strip())
        cleaned = _clean_secret(value)
        if cleaned is not None:
            values[key] = cleaned
    return values


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _clean_secret(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


if __name__ == "__main__":
    main()
