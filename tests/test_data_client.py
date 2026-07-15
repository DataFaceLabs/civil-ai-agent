"""Tests for DataApiClient configuration."""

import httpx
import respx

from civilai_agent.tools.data_client import DataApiClient


@respx.mock
def test_get_section_facts_normalizes_prompt_lab_parcel_step_key() -> None:
    """UAT (2026-07-15): civil-ai-platform's Prompt Lab step key "parcel" leaks verbatim
    into the agent's tool call via context.active_section_id, but civil-ai-data's real
    section_id is "parcel-overview" -- the request must go out normalized, not as-is."""
    route = respx.get("http://data.test/v1/sections/parcel-overview/facts/ent-1").mock(
        return_value=httpx.Response(200, json={"section_id": "parcel-overview"})
    )
    client = DataApiClient(base_url="http://data.test")
    client.get_section_facts("ent-1", "parcel")
    assert route.called


@respx.mock
def test_get_section_facts_normalizes_prompt_lab_access_step_key() -> None:
    """Same latent mismatch as "parcel": Prompt Lab's "access" step key has no
    section_id of that name in civil-ai-data -- the real one is "mobility"."""
    route = respx.get("http://data.test/v1/sections/mobility/facts/ent-1").mock(
        return_value=httpx.Response(200, json={"section_id": "mobility"})
    )
    client = DataApiClient(base_url="http://data.test")
    client.get_section_facts("ent-1", "access")
    assert route.called


@respx.mock
def test_get_section_facts_passes_through_already_valid_section_id() -> None:
    route = respx.get("http://data.test/v1/sections/zoning/facts/ent-1").mock(
        return_value=httpx.Response(200, json={"section_id": "zoning"})
    )
    client = DataApiClient(base_url="http://data.test")
    client.get_section_facts("ent-1", "zoning")
    assert route.called


def test_data_api_client_timeout_defaults_to_30(monkeypatch) -> None:
    monkeypatch.delenv("CIVILAI_DATA_API_TIMEOUT", raising=False)
    client = DataApiClient(base_url="http://data.test")
    assert client.timeout == 30.0


def test_data_api_client_timeout_from_env(monkeypatch) -> None:
    monkeypatch.setenv("CIVILAI_DATA_API_TIMEOUT", "180")
    client = DataApiClient(base_url="http://data.test")
    assert client.timeout == 180.0


def test_data_api_client_explicit_timeout_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("CIVILAI_DATA_API_TIMEOUT", "180")
    client = DataApiClient(base_url="http://data.test", timeout=45.0)
    assert client.timeout == 45.0
