"""Tests for fact tools with mocked data API.

These assert the *outgoing contract* (request body, route path), not just that a mocked
URL returned 200 — the gap audit F4 flagged: the old test matched on URL alone and passed
green over the live 422 caused by sending prop_id instead of parcel_id.
"""

import json

import httpx
import respx

from civilai_agent.tools.data_client import DataApiClient
from civilai_agent.tools.facts import (
    get_section_facts,
    get_site_payload,
    resolve_parcel,
    set_data_client,
)


@respx.mock
def test_resolve_parcel_by_address_sends_address() -> None:
    route = respx.post("http://data.test/v1/entities/resolve").mock(
        return_value=httpx.Response(200, json={"entity_id": "abc-123", "status": "ok"})
    )
    set_data_client(DataApiClient(base_url="http://data.test"))
    result = resolve_parcel(address="123 Main St, Austin, TX")

    assert route.called
    sent = json.loads(route.calls[0].request.content)
    assert sent == {"address": "123 Main St, Austin, TX"}
    payload = json.loads(result)
    assert payload["status"] == "ok"
    assert payload["data"]["entity_id"] == "abc-123"


@respx.mock
def test_resolve_parcel_by_id_sends_parcel_id_not_prop_id() -> None:
    """The backend EntityResolveRequest is extra='forbid' and accepts parcel_id, not prop_id.

    This is the exact regression the audit's F4 said the suite could not catch.
    """
    route = respx.post("http://data.test/v1/entities/resolve").mock(
        return_value=httpx.Response(200, json={"entity_id": "ent-9"})
    )
    set_data_client(DataApiClient(base_url="http://data.test"))
    resolve_parcel(parcel_id="102902")

    sent = json.loads(route.calls[0].request.content)
    assert sent == {"parcel_id": "102902"}
    assert "prop_id" not in sent


@respx.mock
def test_get_site_payload_uses_by_entity_route() -> None:
    """The composed site payload comes from GET /v1/fe/site/by-entity/{id}, not ?entity_id=."""
    route = respx.get("http://data.test/v1/fe/site/by-entity/ent-1").mock(
        return_value=httpx.Response(200, json={"parcel": []})
    )
    set_data_client(DataApiClient(base_url="http://data.test"))
    result = get_site_payload("ent-1")

    assert route.called
    payload = json.loads(result)
    assert payload["status"] == "ok"


@respx.mock
def test_get_section_facts_tool() -> None:
    respx.get("http://data.test/v1/sections/zoning/facts/ent-1").mock(
        return_value=httpx.Response(
            200,
            json={"entity_id": "ent-1", "section_id": "zoning", "facts": {"ZONING_REGS": "LI"}},
        )
    )
    set_data_client(DataApiClient(base_url="http://data.test"))
    result = get_section_facts("ent-1", "zoning")
    payload = json.loads(result)
    assert payload["status"] == "ok"
    assert payload["data"]["section_id"] == "zoning"


@respx.mock
def test_tool_returns_structured_error_on_backend_rejection() -> None:
    """A 422/4xx becomes a structured error result, not a raised exception that crashes the run."""
    respx.post("http://data.test/v1/entities/resolve").mock(
        return_value=httpx.Response(422, json={"detail": "parcel_id must be non-empty"})
    )
    set_data_client(DataApiClient(base_url="http://data.test"))
    result = resolve_parcel(parcel_id="x")
    payload = json.loads(result)
    assert payload["status"] == "error"
    assert payload["status_code"] == 422
    assert "parcel_id" in payload["error"]


def test_resolve_parcel_requires_input() -> None:
    result = resolve_parcel()
    payload = json.loads(result)
    assert payload["status"] == "error"
