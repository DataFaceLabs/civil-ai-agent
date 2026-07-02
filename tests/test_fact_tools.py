"""Tests for fact tools with mocked data API."""

import json

import httpx
import respx

from civilai_agent.tools.data_client import DataApiClient
from civilai_agent.tools.facts import get_section_facts, resolve_parcel, set_data_client


@respx.mock
def test_resolve_parcel_tool() -> None:
    route = respx.post("http://data.test/v1/entities/resolve").mock(
        return_value=httpx.Response(200, json={"entity_id": "abc-123", "status": "ok"})
    )
    set_data_client(DataApiClient(base_url="http://data.test"))
    result = resolve_parcel(address="123 Main St, Austin, TX")
    assert route.called
    payload = json.loads(result)
    assert payload["entity_id"] == "abc-123"


@respx.mock
def test_get_section_facts_tool() -> None:
    respx.get("http://data.test/v1/sections/zoning/facts/ent-1").mock(
        return_value=httpx.Response(
            200,
            json={"entity_id": "ent-1", "section_id": "zoning", "facts": {"ZONING_DISTRICT": "LI"}},
        )
    )
    set_data_client(DataApiClient(base_url="http://data.test"))
    result = get_section_facts("ent-1", "zoning")
    payload = json.loads(result)
    assert payload["section_id"] == "zoning"
