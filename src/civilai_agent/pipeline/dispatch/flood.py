"""Flood branch dispatcher (Phase 4)."""

from __future__ import annotations

import re
from typing import Any

from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.specs import DraftSpec, MissingInput

_SFHA_ZONES = frozenset({"A", "AE", "AO", "AH", "VE", "AR", "A99", "V"})
_NON_SFHA_ZONES = frozenset({"X", "X500", "B", "C", "D"})

_FIPS_COUNTY: dict[str, str] = {
    "48021": "Bastrop",
    "48053": "Burnet",
    "48055": "Caldwell",
    "48209": "Hays",
    "48453": "Travis",
    "48491": "Williamson",
}

_PANEL_GAP = MissingInput(
    name="firm_panel_id",
    why_needed="The FEMA master stem cites the FIRM Community Panel Number.",
    resolution="data-gap",
)
_DATE_GAP = MissingInput(
    name="firm_panel_effective_date",
    why_needed="The FEMA master stem cites the panel effective date.",
    resolution="data-gap",
)
_PROPOSED_WORK_GAP = MissingInput(
    name="proposed_work_scope",
    why_needed=(
        "Floodplain study requirements depend on whether proposed work touches "
        "a floodplain — not the FEMA zone alone."
    ),
    resolution="client",
)
_FLOODWAY_UNKNOWN_GAP = MissingInput(
    name="floodway_flag",
    why_needed="Regulatory floodway status is unknown; encroachment rules cannot be confirmed.",
    resolution="data-gap",
)


def _inner_facts(facts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(facts, dict):
        return {}
    inner = facts.get("facts")
    if isinstance(inner, dict):
        return inner
    return facts


def _normalize_code(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("null", "none"):
        return None
    return text


def _normalize_zone(value: Any) -> str | None:
    code = _normalize_code(value)
    if code is None:
        return None
    return code.upper().split()[0]


def _county_from_panel(panel: str | None) -> str | None:
    if not panel:
        return None
    match = re.match(r"^(\d{5})", panel.strip())
    if not match:
        return None
    return _FIPS_COUNTY.get(match.group(1))


def _county_from_evidence(facts_payload: dict[str, Any]) -> str | None:
    evidence = facts_payload.get("evidence")
    if not isinstance(evidence, dict):
        return None
    for entries in evidence.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            record_id = entry.get("source_record_id")
            if isinstance(record_id, str):
                county = _county_from_panel(record_id)
                if county:
                    return county
    return None


def _floodway_value(inner: dict[str, Any]) -> bool | None:
    raw = inner.get("floodway_flag")
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in ("true", "yes", "1"):
            return True
        if lowered in ("false", "no", "0"):
            return False
    return None


def _determination_items(ctx: SectionContext) -> list[dict[str, Any]]:
    data = ctx.determinations
    if isinstance(data, dict):
        items = data.get("determinations")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _relevant_determinations(ctx: SectionContext) -> list[dict[str, Any]]:
    flood_ids = {"sfha", "floodway"}
    return [item for item in _determination_items(ctx) if item.get("determination_id") in flood_ids]


def _build_citations(facts_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(facts_payload, dict):
        return []
    evidence = facts_payload.get("evidence")
    if not isinstance(evidence, dict):
        return []
    citations: list[dict[str, Any]] = []
    for field, entries in evidence.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = entry.get("citation_url")
            if not url:
                continue
            citations.append(
                {
                    "field": field,
                    "source_name": entry.get("source_name"),
                    "source_id": entry.get("source_id"),
                    "url": url,
                }
            )
    return citations


def _panel_data_gaps(panel_id: str | None, effective_date: str | None) -> list[MissingInput]:
    gaps: list[MissingInput] = []
    if panel_id is None:
        gaps.append(_PANEL_GAP)
    if effective_date is None:
        gaps.append(_DATE_GAP)
    return gaps


def dispatch_flood(ctx: SectionContext) -> DraftSpec:
    """Map governed flood facts to a DraftSpec branch."""
    inner = _inner_facts(ctx.facts)
    zone = _normalize_zone(inner.get("fema_zone"))
    panel_id = _normalize_code(inner.get("panel_id"))
    effective_date = _normalize_code(inner.get("effective_date"))
    floodway = _floodway_value(inner)
    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else {}
    county = _county_from_panel(panel_id) or _county_from_evidence(facts_payload)

    slots: dict[str, str | None] = {
        "flood_zone": zone,
        "fema_zone": zone,
        "panel_id": panel_id,
        "effective_date": effective_date,
        "county_name": county,
        "floodway_flag": None if floodway is None else str(floodway).lower(),
    }

    missing_inputs: list[MissingInput] = []
    citations = _build_citations(facts_payload)
    determinations = _relevant_determinations(ctx)

    if zone is None:
        branch_id = "flood.unknown"
        tier = 2
        stems = [
            "State that FEMA flood zone could not be confirmed from governed data.",
            "Do not assert the parcel is inside or outside the 100-year floodplain.",
        ]
        missing_inputs = [_PANEL_GAP, _DATE_GAP]
    elif zone in _SFHA_ZONES:
        branch_id = "flood.sfha"
        tier = 2
        stems = [
            f"Lead with SFHA status for Zone {zone}.",
            "Emit FS1: a floodplain study may be required if proposed work touches "
            "designated floodplain areas — dispatch on proposed-work scope, not zone alone.",
            "Do not emit the full FS4 study block unless proposed work scope confirms "
            "encroachment; proposed use/scope is not specified.",
            "When panel or effective date are absent, state they could not be confirmed "
            "from governed data.",
        ]
        missing_inputs = [_PROPOSED_WORK_GAP, *_panel_data_gaps(panel_id, effective_date)]
        if floodway is None:
            missing_inputs.append(_FLOODWAY_UNKNOWN_GAP)
        elif floodway is False:
            stems.append("State that regulatory floodway is not mapped on the parcel.")
        else:
            stems.append(
                "State that regulatory floodway is present; encroachment restrictions apply."
            )
    elif zone in _NON_SFHA_ZONES:
        branch_id = "flood.zone_x"
        tier = 1
        stems = [
            "Render the FEMA master stem for Zone X (minimal flood hazard).",
            "When panel or effective date are absent, state they could not be confirmed "
            "from governed data — never invent a panel number or date.",
        ]
        missing_inputs = _panel_data_gaps(panel_id, effective_date)
        if floodway is None:
            missing_inputs.append(_FLOODWAY_UNKNOWN_GAP)
    else:
        branch_id = "flood.unknown"
        tier = 2
        stems = [
            f"State that FEMA Zone {zone} was returned but is not mapped to a known branch.",
            "Recommend manual FIRM verification; do not assert SFHA status.",
        ]
        missing_inputs = _panel_data_gaps(panel_id, effective_date)

    return DraftSpec(
        entity_id=ctx.entity_id,
        section_id="flood",
        branch_id=branch_id,
        tier=tier,
        slots=slots,
        facts=facts_payload,
        determinations=determinations,
        citations=citations,
        stems=stems,
        missing_inputs=missing_inputs,
        searchable_gaps=[],
    )
