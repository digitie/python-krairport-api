"""KAC 스타일 공공데이터 XML 응답 도우미."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from xml.etree import ElementTree

from pykrairport._convert import as_list
from pykrairport.exceptions import KrairportParseError


def parse_xml(text: str) -> dict[str, Any]:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise KrairportParseError(f"failed to parse XML response: {exc}") from exc
    return {_strip_namespace(root.tag): _element_to_data(root)}


def extract_items(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    response = data.get("response", data)
    if not isinstance(response, Mapping):
        raise KrairportParseError("XML response does not contain a response object")
    body = response.get("body")
    if not isinstance(body, Mapping):
        return []
    items = body.get("items")
    if not isinstance(items, Mapping):
        return []
    item_values = as_list(items.get("item"))
    rows: list[dict[str, Any]] = []
    for item in item_values:
        if not isinstance(item, dict):
            raise KrairportParseError("XML item is not an object")
        rows.append(item)
    return rows


def response_header(data: Mapping[str, Any]) -> Mapping[str, Any]:
    response = data.get("response", data)
    if not isinstance(response, Mapping):
        return {}
    header = response.get("header")
    return header if isinstance(header, Mapping) else {}


def _element_to_data(element: ElementTree.Element) -> Any:
    children = list(element)
    if not children:
        return (element.text or "").strip()

    grouped: dict[str, Any] = {}
    for child in children:
        key = _strip_namespace(child.tag)
        value = _element_to_data(child)
        if key in grouped:
            existing = grouped[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                grouped[key] = [existing, value]
        else:
            grouped[key] = value
    return grouped


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
