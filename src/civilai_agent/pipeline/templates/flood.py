"""Flood Tier-1 FEMA master stem (Phase 4) — no LLM."""

from __future__ import annotations

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.pipeline.specs import DraftSpec
from civilai_agent.pipeline.templates.format import headed_section

_TIER1_BRANCHES = frozenset({"flood.zone_x"})

_PANEL_GAP_TEXT = (
    "FIRM Community Panel Number and effective date could not be confirmed from governed data."
)


def _county_label(spec: DraftSpec) -> str:
    county = spec.slots.get("county_name")
    if county:
        return str(county)
    return "the subject"


def _zone_outcome(zone: str | None) -> str:
    normalized = (zone or "X").upper()
    if normalized == "X":
        return "within Zone X, an area of minimal flood hazard"
    return (
        f"outside the Special Flood Hazard Area (Zone {normalized}, "
        "minimal or undetermined flood hazard)"
    )


def _panel_sentence(spec: DraftSpec) -> str:
    panel = spec.slots.get("panel_id")
    date = spec.slots.get("effective_date")
    county = _county_label(spec)
    zone = spec.slots.get("flood_zone") or spec.slots.get("fema_zone")
    outcome = _zone_outcome(str(zone) if zone else None)

    if panel and date:
        return (
            f"According to the Flood Insurance Rate Map (FIRM) for {county} County, Texas, "
            f"Community Panel Number {panel}, Effective {date}, the property is {outcome}."
        )
    if panel:
        return (
            f"According to the Flood Insurance Rate Map (FIRM) for {county} County, Texas, "
            f"Community Panel Number {panel}, the property is {outcome}. "
            f"FIRM panel effective date could not be confirmed from governed data."
        )
    return (
        f"According to the Flood Insurance Rate Map (FIRM) for {county} County, Texas, "
        f"the property is {outcome}. {_PANEL_GAP_TEXT}"
    )


def _data_gaps(spec: DraftSpec) -> tuple[str, ...]:
    gaps: list[str] = []
    for item in spec.missing_inputs:
        if item.resolution == "data-gap":
            gaps.append(item.why_needed)
    return tuple(gaps)


def _verification_steps(spec: DraftSpec) -> tuple[str, ...]:
    steps: list[str] = []
    for item in spec.missing_inputs:
        if item.resolution == "data-gap":
            steps.append(f"Obtain {item.name} from FEMA NFHL / FIRMette records.")
    if not steps:
        steps.append("Confirm FIRM panel and zone designation with current NFHL data.")
    return tuple(steps)


def render_flood_tier1(spec: DraftSpec) -> SectionDraftOutput:
    """Render the FEMA master stem for Tier-1 flood branches without an LLM."""
    if spec.branch_id not in _TIER1_BRANCHES:
        msg = f"No Tier-1 template for branch {spec.branch_id!r}"
        raise ValueError(msg)
    if spec.tier != 1:
        msg = f"Tier-1 template requires tier=1, got {spec.tier}"
        raise ValueError(msg)

    statement = _panel_sentence(spec)
    floodway = spec.slots.get("floodway_flag")
    if floodway == "false":
        statement += " Regulatory floodway is not mapped on the parcel."

    language = headed_section("Flood", [("FEMA Flood Zone", statement)])

    caveats: list[str] = []
    if any(m.name == "firm_panel_id" for m in spec.missing_inputs):
        caveats.append(_PANEL_GAP_TEXT)

    return SectionDraftOutput(
        suggested_language=language,
        caveats=tuple(caveats),
        verification_steps=_verification_steps(spec),
        data_gaps=_data_gaps(spec),
        sources=(),
    )
