"""Format-parity gate: no template-path section render may be flat, unheaded prose.

Template-tier branches (rural/ETJ zoning, Edwards-outside environmental, Zone-X flood) build
prose in Python with no LLM call. They must still carry the same markdown heading structure
the LLM render path produces, so a deterministic branch does not come back as a bare sentence
next to fully-formatted sections. This gate fails loudly if a template regresses to flat prose.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.pipeline.specs import DraftSpec
from civilai_agent.pipeline.templates.environmental import render_environmental_tier1
from civilai_agent.pipeline.templates.flood import render_flood_tier1
from civilai_agent.pipeline.templates.zoning import render_zoning_tier0


def _spec(section_id: str, branch_id: str, tier: int, slots: dict[str, str | None]) -> DraftSpec:
    return DraftSpec(
        entity_id="ent-1", section_id=section_id, branch_id=branch_id, tier=tier, slots=slots
    )


def _zoning_county() -> SectionDraftOutput:
    return render_zoning_tier0(
        _spec("zoning", "zoning.county_no_zoning", 0, {"jurisdiction_primary": "Travis County"})
    )


def _zoning_etj() -> SectionDraftOutput:
    return render_zoning_tier0(
        _spec("zoning", "zoning.etj", 0, {"jurisdiction_primary": "City of Kyle (ETJ)"})
    )


def _flood_zone_x() -> SectionDraftOutput:
    return render_flood_tier1(
        _spec(
            "flood",
            "flood.zone_x",
            1,
            {"fema_zone": "X", "county_name": "Travis", "floodway_flag": "false"},
        )
    )


def _environmental_edwards() -> SectionDraftOutput:
    return render_environmental_tier1(
        _spec(
            "environmental",
            "environmental.edwards_outside",
            1,
            {
                "watershed_name": "Walnut Creek",
                "in_travis_county": "true",
                "cwqz_setback_ft": "300",
                "waterway_name": "Maha Creek",
            },
        )
    )


_TEMPLATE_RENDERS: dict[str, Callable[[], SectionDraftOutput]] = {
    "zoning.county_no_zoning": _zoning_county,
    "zoning.etj": _zoning_etj,
    "flood.zone_x": _flood_zone_x,
    "environmental.edwards_outside": _environmental_edwards,
}


@pytest.mark.parametrize("branch", sorted(_TEMPLATE_RENDERS))
def test_template_render_carries_heading_structure(branch: str) -> None:
    text = _TEMPLATE_RENDERS[branch]().suggested_language
    assert text.startswith("# "), f"{branch}: missing h1 section heading"
    assert "\n## " in text, f"{branch}: missing h2 subsection heading (flat prose)"
    # Real content must sit beneath the headings, not just bare header lines.
    body_lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    assert body_lines, f"{branch}: headings with no body content"
