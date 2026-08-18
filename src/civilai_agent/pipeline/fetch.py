"""Deterministic fetch: section facts, determinations, provenance."""

from __future__ import annotations

import re
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
    related_facts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    hydrate_impervious_status: str | None = None


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

    if section_id in ("environmental", "flood"):
        try:
            ctx.related_facts["jurisdiction"] = client.get_section_facts(entity_id, "jurisdiction")
        except DataApiError as exc:
            ctx.errors.append(f"jurisdiction facts (related): {exc}")

    return ctx


_PLACE_KEYS: tuple[tuple[str, str], ...] = (
    ("dripping springs", "dripping_springs"),
    ("san marcos", "san_marcos"),
    ("round rock", "round_rock"),
    ("cedar park", "cedar_park"),
    ("pflugerville", "pflugerville"),
    ("georgetown", "georgetown"),
    ("smithville", "smithville"),
    ("lockhart", "lockhart"),
    ("leander", "leander"),
    ("bastrop", "city_of_bastrop"),
    ("austin", "coa_full"),
    ("luling", "luling"),
    ("elgin", "elgin"),
    ("buda", "buda"),
    ("kyle", "kyle"),
)

_FALSE_IC_GAP = (
    "no tiered impervious cover table",
    "watershed tier is available in current records",
)


def _inner_facts(facts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(facts, dict):
        return {}
    inner = facts.get("facts")
    if isinstance(inner, dict):
        return dict(inner)
    return dict(facts)


def _with_inner_facts(facts: dict[str, Any] | None, inner: dict[str, Any]) -> dict[str, Any]:
    if isinstance(facts, dict) and isinstance(facts.get("facts"), dict):
        return {**facts, "facts": inner}
    return inner


def jurisdiction_key_from_text(text: str | None) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    for needle, key in _PLACE_KEYS:
        if needle in lowered:
            return key
    return None


def zoning_code_from_text(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"\b([A-Z]{1,4}-?\d[A-Z0-9-]*)\b", str(text))
    return match.group(1) if match else None


def merge_impervious_hydrate(
    client: DataApiClient,
    ctx: SectionContext,
    field_context: dict[str, str] | None = None,
) -> SectionContext:
    """Stamp hydrate IMPERVIOUS_REGS / COVER_LIMIT onto zoning section facts."""
    if ctx.section_id != "zoning":
        return ctx
    inner = _inner_facts(ctx.facts)
    fields = field_context or {}
    juris = (
        jurisdiction_key_from_text(fields.get("GOVERNING_JURIS"))
        or jurisdiction_key_from_text(str(inner.get("GOVERNING_JURIS") or ""))
        or jurisdiction_key_from_text(str(inner.get("jurisdiction_primary") or ""))
    )
    zoning = (
        zoning_code_from_text(fields.get("ZONING_REGS"))
        or zoning_code_from_text(str(inner.get("ZONING_REGS") or ""))
        or zoning_code_from_text(str(inner.get("zoning_code") or ""))
    )
    if not juris or not zoning:
        return ctx
    try:
        payload = client.hydrate_regtext(juris, zoning, ["impervious"])
    except DataApiError as exc:
        ctx.errors.append(f"hydrate_regtext: {exc}")
        return ctx
    families = payload.get("families") if isinstance(payload, dict) else None
    family = families.get("impervious") if isinstance(families, dict) else None
    if not isinstance(family, dict):
        return ctx
    status = str(family.get("status") or "")
    ctx = ctx.model_copy(update={"hydrate_impervious_status": status})
    if status not in {"complete", "partial"}:
        return ctx
    regs = str(family.get("regs_text") or "").strip()
    pct = family.get("limit_pct")
    if regs:
        inner["IMPERVIOUS_REGS"] = regs
        inner["impervious_regs"] = regs
    if pct is not None:
        inner["IMPERVIOUS_COVER_LIMIT"] = f"{float(pct):g}%"
    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else None
    return ctx.model_copy(update={"facts": _with_inner_facts(facts_payload, inner)})


def false_ic_gap_warning(draft: str, hydrate_status: str | None) -> str | None:
    """Flag the known Austin-shaped gap sentence when hydrate found a schedule."""
    if hydrate_status not in {"complete", "partial"}:
        return None
    lowered = draft.lower()
    if any(needle in lowered for needle in _FALSE_IC_GAP):
        return (
            "Draft claims no tiered impervious-cover table, but hydrate found an "
            "indexed schedule. Do not treat watershed-tier absence as a local gap."
        )
    return None
