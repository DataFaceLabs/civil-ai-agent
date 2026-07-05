"""Zoning Tier-0 stems (Phase 3) — no LLM."""

from __future__ import annotations

import re

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.pipeline.dispatch.zoning import STEM_B_COUNTY, STEM_C_ETJ
from civilai_agent.pipeline.specs import DraftSpec

_TIER0_BRANCHES = frozenset({"zoning.county_no_zoning", "zoning.etj"})


def _county_name(slots: dict[str, str | None]) -> str:
    juris = slots.get("jurisdiction_primary") or "the"
    match = re.match(r"^(.+?)\s+County", juris, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return juris.strip()


def _etj_city(slots: dict[str, str | None]) -> str:
    juris = slots.get("jurisdiction_primary") or "the city"
    return re.sub(r"\s*\(ETJ\)\s*$", "", juris, flags=re.IGNORECASE).strip()


def _jurisdiction_caveat(spec: DraftSpec) -> str:
    juris = spec.slots.get("jurisdiction_primary") or "governed jurisdiction records"
    return f"Jurisdiction classification is based on governed data ({juris})."


def _verification_steps(spec: DraftSpec) -> tuple[str, ...]:
    common = (
        "Confirm jurisdiction boundaries against county or municipal GIS records.",
        "Check for unrecorded zoning overlays, annexation agreements, or PUD regimes "
        "in title commitments or survey exhibits.",
    )
    if spec.branch_id == "zoning.county_no_zoning":
        return (
            *common,
            "Verify county subdivision platting and OSSF requirements with the "
            "governing county authority.",
        )
    return (
        *common,
        "Verify ETJ boundary and any annexation agreement terms with the city.",
    )


def render_zoning_tier0(spec: DraftSpec) -> SectionDraftOutput:
    """Render fixed Stem B/C prose for Tier-0 zoning branches without an LLM."""
    if spec.branch_id not in _TIER0_BRANCHES:
        msg = f"No Tier-0 template for branch {spec.branch_id!r}"
        raise ValueError(msg)
    if spec.tier != 0:
        msg = f"Tier-0 template requires tier=0, got {spec.tier}"
        raise ValueError(msg)

    if spec.branch_id == "zoning.county_no_zoning":
        language = STEM_B_COUNTY.format(county=_county_name(spec.slots))
    else:
        language = STEM_C_ETJ.format(city=_etj_city(spec.slots))

    return SectionDraftOutput(
        suggested_language=language,
        caveats=(_jurisdiction_caveat(spec),),
        verification_steps=_verification_steps(spec),
        data_gaps=(),
        sources=(),
    )
