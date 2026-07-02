"""Strands tools for governed backend facts."""

from __future__ import annotations

import json
from typing import Any

from strands import tool

from civilai_agent.tools.data_client import DataApiClient

_client: DataApiClient | None = None


def get_data_client() -> DataApiClient:
    global _client
    if _client is None:
        _client = DataApiClient()
    return _client


def set_data_client(client: DataApiClient) -> None:
    global _client
    _client = client


@tool
def resolve_parcel(address: str = "", prop_id: str = "") -> str:
    """Resolve a street address or Travis CAD prop_id to an entity_id.

    Use this before any other fact tool when entity_id is unknown.
    """
    if not address.strip() and not prop_id.strip():
        return json.dumps({"error": "Provide address or prop_id"})
    client = get_data_client()
    payload = client.resolve_parcel(
        address=address.strip() or None,
        prop_id=prop_id.strip() or None,
    )
    return json.dumps(payload)


@tool
def get_section_facts(entity_id: str, section_id: str) -> str:
    """Fetch governed section facts for an entity (zoning, flood, utilities, etc.)."""
    client = get_data_client()
    payload = client.get_section_facts(entity_id, section_id)
    return json.dumps(payload)


@tool
def get_site_payload(entity_id: str) -> str:
    """Fetch the composed FE SitePayload for drafting context."""
    client = get_data_client()
    payload = client.get_site_by_entity(entity_id)
    return json.dumps(payload)


@tool
def get_provenance(entity_id: str) -> str:
    """Fetch provenance metadata for an entity's facts."""
    client = get_data_client()
    payload = client.get_provenance(entity_id)
    return json.dumps(payload)


@tool
def run_determinations(entity_id: str) -> str:
    """Evaluate determination contracts over entity facts (grounded conclusions)."""
    client = get_data_client()
    payload = client.run_determinations(entity_id)
    return json.dumps(payload)
