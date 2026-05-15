from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from krairport import KrairportClient, __version__, api_catalog
from krairport.debug import DEBUGGABLE_FUNCTIONS, jsonable
from pydantic import BaseModel

from fixture_writer import build_fixture, save_fixture

ENV_KEY_NAMES = ("KAC_SERVICE_KEY", "IIAC_SERVICE_KEY")

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


def main() -> None:
    st.set_page_config(page_title="Krairport Debug UI", layout="wide")
    st.title("Krairport Debug UI")
    env_defaults = _load_local_env()

    with st.sidebar:
        function_name = st.selectbox(
            "Function",
            sorted(name for name in DEBUGGABLE_FUNCTIONS if name in FIELD_SPECS),
        )
        environment = st.selectbox("Environment", ["manual", "env"])
        kac_key = st.text_input(
            "KAC service key",
            value=env_defaults.get("KAC_SERVICE_KEY", ""),
            type="password",
        )
        iiac_key = st.text_input(
            "IIAC service key",
            value=env_defaults.get("IIAC_SERVICE_KEY", ""),
            type="password",
        )
        _service_key_links(function_name)
        timeout = st.number_input("Timeout", min_value=1.0, max_value=120.0, value=10.0)
        fixture_base_dir = st.text_input(
            "Fixture base dir",
            value=str((_repo_root() / "tests/fixtures").resolve()),
        )

    with st.form("run-form"):
        input_data = _render_inputs(function_name)
        submitted = st.form_submit_button("Run")

    if submitted:
        client = _client(environment, kac_key, iiac_key, timeout)
        st.session_state["debug_run"] = client.debug(function_name, **input_data)

    run = st.session_state.get("debug_run")
    raw_tab, parsed_tab, processed_tab, error_tab, trace_tab, fixture_tab = st.tabs(
        [
            "Raw Response",
            "Pydantic Model",
            "Processed Result",
            "Validation Errors",
            "Debug Trace",
            "Fixture",
        ]
    )

    with raw_tab:
        _show_json(run.response if run else {})
    with parsed_tab:
        _show_result(run.parsed if run else None)
    with processed_tab:
        _show_result(run.processed if run else None)
    with error_tab:
        _show_json(run.error if run and run.error else {})
    with trace_tab:
        _show_json(run.trace if run else [])
        _catalog_panel(function_name)
    with fixture_tab:
        if run is not None and run.error is None:
            _fixture_panel(run, function_name, fixture_base_dir)


def _client(
    environment: str,
    kac_key: str | None,
    iiac_key: str | None,
    timeout: float,
) -> KrairportClient:
    if environment == "env":
        defaults = _load_local_env()
        return KrairportClient(
            kac_service_key=defaults.get("KAC_SERVICE_KEY"),
            iiac_service_key=defaults.get("IIAC_SERVICE_KEY"),
            timeout=timeout,
        )
    return KrairportClient(
        kac_service_key=_clean_secret(kac_key),
        iiac_service_key=_clean_secret(iiac_key),
        timeout=timeout,
    )


def _render_inputs(function_name: str) -> dict[str, Any]:
    cols = st.columns(2)
    values: dict[str, Any] = {}
    for index, (name, kind, default) in enumerate(FIELD_SPECS[function_name]):
        with cols[index % 2]:
            value = _field(name, kind, default)
        if value is not None:
            values[name] = value
    return values


def _field(name: str, kind: str, default: Any) -> Any:
    if kind == "int":
        return int(st.number_input(name, value=int(default), step=1))
    if kind == "bool":
        return st.checkbox(name, value=bool(default))
    if kind == "optional_bool":
        selected = st.selectbox(name, ["auto", "true", "false"])
        return {"auto": None, "true": True, "false": False}[selected]
    if kind == "select":
        return st.selectbox(name, ["arrival", "departure"], index=0 if default == "arrival" else 1)
    value = st.text_input(name, value=str(default))
    return value.strip() or None


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


def _catalog_panel(function_name: str) -> None:
    rows = _catalog_rows(function_name)
    st.subheader("API Catalog")
    if not rows:
        st.info("No catalog entries for this function.")
        return
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
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


def _service_key_links(function_name: str) -> None:
    items = api_catalog(function_name)
    if not items:
        return
    st.caption("Service key links")
    for item in items:
        st.link_button(
            f"{str(item.provider).upper()} · {item.dataset_name}",
            item.service_key_url,
            use_container_width=True,
        )


def _catalog_rows(function_name: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in api_catalog(function_name):
        rows.append(
            {
                "provider": str(item.provider),
                "dataset_name": item.dataset_name,
                "service": item.service,
                "operation": item.operation,
                "response_format": item.response_format,
                "service_key_url": item.service_key_url,
                "endpoint": item.endpoint,
                "notes": item.notes,
            }
        )
    return rows


def _fixture_panel(run: Any, function_name: str, fixture_base_dir: str) -> None:
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
    return [
        app_dir / ".env",
        _repo_root() / ".env",
    ]


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
        key = key.strip()
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
