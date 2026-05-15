from __future__ import annotations

import json

import pytest

from app import _catalog_rows, _clean_secret, _load_local_env
from fixture_writer import build_fixture, save_fixture, slugify


def test_slugify_keeps_safe_case_name() -> None:
    assert slugify("Search Busan Festival Normal") == "search-busan-festival-normal"


def test_save_fixture_redacts_sensitive_values_and_blocks_overwrite(tmp_path) -> None:
    path = save_fixture(
        base_dir=tmp_path,
        function_name="departures",
        case_name="Normal Case",
        description="fixture writer test",
        input_data={"airport_code": "GMP", "serviceKey": "secret"},
        request_data={"headers": {"Authorization": "Bearer token"}},
        response_data={"body": [{"flightId": "KE1201"}]},
        parsed_result=[{"flight_id": "KE1201"}],
        processed_result=[{"flight_id": "KE1201"}],
        library_version="0.1.0",
    )

    data = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "normal-case.json"
    assert data["input"]["serviceKey"] == "<REDACTED>"
    assert data["request"]["headers"]["Authorization"] == "<REDACTED>"
    with pytest.raises(FileExistsError):
        save_fixture(
            base_dir=tmp_path,
            function_name="departures",
            case_name="Normal Case",
            description="fixture writer test",
            input_data={},
            request_data={},
            response_data={},
            parsed_result={},
            processed_result={},
        )


def test_build_fixture_uses_snapshot_default() -> None:
    fixture = build_fixture(
        function_name="parking_status",
        case_name="Parking",
        description="",
        input_data={},
        request_data={},
        response_data={},
        parsed_result={},
        processed_result={},
    )

    assert fixture["assertion"]["mode"] == "snapshot"


def test_load_local_env_uses_dotenv_values(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("KAC_SERVICE_KEY", raising=False)
    monkeypatch.delenv("IIAC_SERVICE_KEY", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        'KAC_SERVICE_KEY="  KAC_FROM_FILE  "\nIIAC_SERVICE_KEY= IIAC_FROM_FILE \n',
        encoding="utf-8",
    )

    values = _load_local_env([dotenv])

    assert values == {
        "KAC_SERVICE_KEY": "KAC_FROM_FILE",
        "IIAC_SERVICE_KEY": "IIAC_FROM_FILE",
    }


def test_clean_secret_strips_copy_paste_whitespace() -> None:
    assert _clean_secret("  KEY\r\n") == "KEY"
    assert _clean_secret(" \t ") is None


def test_catalog_rows_include_human_dataset_name_and_key_link() -> None:
    rows = _catalog_rows("parking_status")

    assert {row["dataset_name"] for row in rows} >= {
        "한국공항공사 전국공항 주차장 혼잡도",
        "인천국제공항공사 주차 정보",
    }
    assert all(row["service_key_url"].startswith("https://") for row in rows)
