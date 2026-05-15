from __future__ import annotations

from krairport import ApiCatalogItem, api_catalog


def test_api_catalog_filters_by_function_and_provider() -> None:
    rows = api_catalog("parking_status", provider="iiac")

    assert len(rows) == 1
    assert isinstance(rows[0], ApiCatalogItem)
    assert rows[0].dataset_name == "인천국제공항공사 주차 정보"
    assert rows[0].operation == "getTrackingParking"
    assert rows[0].service_key_url == "https://www.data.go.kr/data/15095047/openapi.do"


def test_api_catalog_exposes_human_readable_dataset_names() -> None:
    rows = api_catalog("departures")

    dataset_names = {row.dataset_name for row in rows}
    assert "한국공항공사 실시간 항공운항 현황 상세 조회" in dataset_names
    assert "인천국제공항공사 여객기 운항 현황 상세 조회 서비스" in dataset_names
    assert all(row.to_dict()["dataset_name"] for row in rows)
    assert all(row.to_dict()["service_key_url"].startswith("https://") for row in rows)
