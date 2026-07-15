"""Strands tools for governed backend facts.

Every tool returns a structured JSON envelope so the model can recover from a failed
call instead of crashing the run: ``{"status": "ok", "data": ...}`` on success, or
``{"status": "error", "error": "...", "status_code": N}`` when the governed-data API
rejects or is unreachable.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from strands import tool

from civilai_agent.tools.data_client import DataApiClient, DataApiError

_client: DataApiClient | None = None


def get_data_client() -> DataApiClient:
    global _client
    if _client is None:
        _client = DataApiClient()
    return _client


def set_data_client(client: DataApiClient) -> None:
    global _client
    _client = client


def _envelope(fetch: Callable[[], Any]) -> str:
    try:
        return json.dumps({"status": "ok", "data": fetch()})
    except DataApiError as exc:
        return json.dumps({"status": "error", "error": str(exc), "status_code": exc.status_code})


@tool
def resolve_parcel(address: str = "", parcel_id: str = "", county: str = "") -> str:
    """Resolve a street address or CAD parcel/account id to an entity_id.

    Use this before any other fact tool when entity_id is unknown. Provide the street
    address, the parcel_id (authoritative CAD account id), or both. When parcel_id is
    set outside Travis, also pass county to avoid cross-county PROP_ID collisions.
    """
    if not address.strip() and not parcel_id.strip():
        return json.dumps({"status": "error", "error": "Provide address or parcel_id"})
    client = get_data_client()
    return _envelope(
        lambda: client.resolve_parcel(
            address=address.strip() or None,
            parcel_id=parcel_id.strip() or None,
            county=county.strip() or None,
        )
    )


@tool
def get_section_facts(entity_id: str, section_id: str) -> str:
    """Fetch governed section facts for an entity.

    Valid section_id values: parcel-overview, zoning, flood, jurisdiction, watershed,
    soils, utilities, mobility, environmental, compliance, provenance. (A caller-facing
    "parcel" or "access" step name is normalized to parcel-overview/mobility for you.)
    """
    client = get_data_client()
    return _envelope(lambda: client.get_section_facts(entity_id, section_id))


@tool
def get_site_payload(entity_id: str) -> str:
    """Fetch the composed FE SitePayload for drafting context."""
    client = get_data_client()
    return _envelope(lambda: client.get_site_by_entity(entity_id))


@tool
def get_provenance(entity_id: str) -> str:
    """Fetch provenance metadata for an entity's facts."""
    client = get_data_client()
    return _envelope(lambda: client.get_provenance(entity_id))


@tool
def run_determinations(entity_id: str) -> str:
    """Evaluate determination contracts over entity facts (grounded conclusions)."""
    client = get_data_client()
    return _envelope(lambda: client.run_determinations(entity_id))
