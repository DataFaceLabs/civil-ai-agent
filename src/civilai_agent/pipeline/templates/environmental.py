"""Environmental Tier-1 stems (Phase 6) — Edwards outside + CWQZ, no LLM."""

from __future__ import annotations

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.pipeline.specs import DraftSpec

_TIER1_BRANCHES = frozenset({"environmental.edwards_outside"})

STEM_EA_OUTSIDE = (
    "This site is located outside the Edwards Aquifer Transition Zone, as defined by the "
    "Texas Commission on Environmental Quality (TCEQ). No additional permits are required "
    "for development activities related to the Edwards Aquifer. The project site is located "
    "outside of the Barton Springs zone."
)


def _watershed_paragraph(spec: DraftSpec) -> str | None:
    watershed = spec.slots.get("watershed_name")
    if not watershed:
        return None
    return (
        f"The property is located within the {watershed} watershed. Regional drainage "
        "criteria and water-quality controls for this watershed apply."
    )


def _ehz_paragraph(spec: DraftSpec) -> str | None:
    if spec.slots.get("erosion_hazard_pending") == "true":
        return (
            "Erosion Hazard Zone (EHZ) overlay classification is pending from governed data; "
            "confirm EHZ applicability with City of Austin GIS before concluding encroachment."
        )
    erosion = spec.slots.get("erosion_hazard")
    if erosion:
        return erosion
    return None


def _cwqz_paragraph(spec: DraftSpec) -> str | None:
    setback = spec.slots.get("cwqz_setback_ft")
    waterway = spec.slots.get("waterway_name")
    classification = spec.slots.get("classification")
    drainage = spec.slots.get("drainage_area_acres")
    in_travis = spec.slots.get("in_travis_county") == "true"

    if not in_travis:
        return None

    if setback:
        parts = [f"A Critical Water Quality Zone (CWQZ) setback of {setback} feet applies"]
        if waterway:
            parts.append(f"along {waterway}")
        if classification:
            detail = f"({classification} waterway"
            if drainage:
                try:
                    ac = float(drainage)
                    detail += f", contributing drainage area approximately {ac:.0f} acres"
                except ValueError:
                    pass
            detail += ", Travis County Code §482.941)"
            parts.append(detail)
        else:
            parts.append("(Travis County Code §482.941).")
        return " ".join(parts) + "."

    if waterway:
        return (
            f"Waterway {waterway} is identified; CWQZ classification or setback could not be "
            "confirmed from governed data."
        )

    return (
        "No jurisdictional waterway requiring a Critical Water Quality Zone setback was "
        "identified from governed data."
    )


def _data_gaps(spec: DraftSpec) -> tuple[str, ...]:
    return tuple(item.why_needed for item in spec.missing_inputs if item.resolution == "data-gap")


def _verification_steps(spec: DraftSpec) -> tuple[str, ...]:
    steps: list[str] = [
        "Confirm Edwards Aquifer zone with the TCEQ Edwards Aquifer viewer.",
        "Verify Barton Springs Zone status with City of Austin GIS when applicable.",
    ]
    if spec.slots.get("watershed_name"):
        steps.append(
            "Confirm watershed classification and applicable drainage/water-quality criteria."
        )
    if spec.slots.get("in_travis_county") == "true" and spec.slots.get("waterway_name"):
        steps.extend(
            [
                "Confirm contributing drainage area and waterway classification for CWQZ setbacks.",
                "Use Travis County Code §482.941 setbacks (100/200/300 ft; Colorado River below "
                "Lady Bird Lake 400 ft) — not legacy 50/100/200 values.",
            ]
        )
    elif spec.slots.get("in_travis_county") == "true" and not spec.slots.get("cwqz_setback_ft"):
        steps.append(
            "Verify off-site CWQZ intermediate waterway buffers with City of Austin GIS."
        )
    if spec.slots.get("erosion_hazard_pending") == "true":
        steps.append("Confirm Erosion Hazard Zone overlay applicability with City of Austin GIS.")
    return tuple(steps)


def render_environmental_tier1(spec: DraftSpec) -> SectionDraftOutput:
    """Render Tier-1 environmental prose (EA-outside stem + CWQZ block) without an LLM."""
    if spec.branch_id not in _TIER1_BRANCHES:
        msg = f"No Tier-1 template for branch {spec.branch_id!r}"
        raise ValueError(msg)
    if spec.tier != 1:
        msg = f"Tier-1 template requires tier=1, got {spec.tier}"
        raise ValueError(msg)

    paragraphs = [STEM_EA_OUTSIDE]
    watershed = _watershed_paragraph(spec)
    if watershed:
        paragraphs.append(watershed)
    cwqz = _cwqz_paragraph(spec)
    if cwqz:
        paragraphs.append(cwqz)
    ehz = _ehz_paragraph(spec)
    if ehz:
        paragraphs.append(ehz)

    return SectionDraftOutput(
        suggested_language="\n\n".join(paragraphs),
        caveats=(),
        verification_steps=_verification_steps(spec),
        data_gaps=_data_gaps(spec),
        sources=(),
    )
