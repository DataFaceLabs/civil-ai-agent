"""Deterministic fetch: section facts, determinations, provenance."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from civilai_agent.tools.data_client import DataApiClient, DataApiError


class SectionContext(BaseModel):
    """Governed data retrieved in Python before any LLM call."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    section_id: str
    facts: dict[str, Any] | None = None
    determinations: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)


def facts_nonempty(facts: dict[str, Any] | None) -> bool:
    """True when governed section facts carry usable field values."""
    if not isinstance(facts, dict):
        return False
    inner = facts.get("facts")
    if isinstance(inner, dict) and inner:
        return True
    return bool(facts.get("entity_id"))


def fetch_section_context(
    client: DataApiClient,
    entity_id: str,
    section_id: str,
) -> SectionContext:
    """Fetch facts, determinations, and provenance; errors are captured, not raised."""
    ctx = SectionContext(entity_id=entity_id, section_id=section_id)
    try:
        ctx.facts = client.get_section_facts(entity_id, section_id)
    except DataApiError as exc:
        ctx.errors.append(f"get_section_facts: {exc}")

    try:
        ctx.determinations = client.run_determinations(entity_id)
    except DataApiError as exc:
        ctx.errors.append(f"run_determinations: {exc}")

    try:
        ctx.provenance = client.get_provenance(entity_id)
    except DataApiError as exc:
        ctx.errors.append(f"get_provenance: {exc}")

    return ctx
