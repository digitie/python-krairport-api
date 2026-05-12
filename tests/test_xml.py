from __future__ import annotations

import pytest

from krairport._xml import extract_items, parse_xml, response_header
from krairport.exceptions import KrairportParseError


def test_extracts_repeated_xml_items(load_fixture) -> None:  # type: ignore[no-untyped-def]
    data = parse_xml(load_fixture("kac_departures.xml"))

    rows = extract_items(data)

    assert len(rows) == 2
    assert rows[0]["flightId"] == "KE1201"
    assert rows[1]["flightId"] == "7C1101"


def test_extracts_single_xml_item_as_list(load_fixture) -> None:  # type: ignore[no-untyped-def]
    data = parse_xml(load_fixture("kac_arrivals_single.xml"))

    rows = extract_items(data)

    assert len(rows) == 1
    assert rows[0]["flightId"] == "OZ8801"


def test_xml_error_paths() -> None:
    with pytest.raises(KrairportParseError):
        parse_xml("<response>")

    assert extract_items({"response": {"body": {}}}) == []
    assert response_header({"response": {"header": {"resultCode": "00"}}})["resultCode"] == "00"

    bad_item = {"response": {"body": {"items": {"item": "not-an-object"}}}}
    with pytest.raises(KrairportParseError):
        extract_items(bad_item)
