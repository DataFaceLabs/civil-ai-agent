"""Contract tests for environmental branch dispatcher (S6.1)."""

from __future__ import annotations

from typing import Any

from civilai_agent.pipeline.dispatch.environmental import dispatch_environmental
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.templates.environmental import (
    STEM_EA_OUTSIDE,
    render_environmental_tier1,
)


def _ctx(
    *, facts: dict[str, Any] | None = None, determinations: dict[str, Any] | None = None
) -> SectionContext:
    return SectionContext(
        entity_id="ent-env",
        section_id="environmental",
        facts=facts,
        determinations=determinations,
    )


_EDWARDS_TCEQ_QUALITY = {"quality": {"flags": ["edwards_overlay_tceq"]}}


def test_wpap_recharge_branch_tier2() -> None:
    spec = dispatch_environmental(
        _ctx(facts={"facts": {"wpap_type": "WPAP", "zone_type": "recharge"}})
    )
    assert spec.branch_id == "environmental.edwards_wpap"
    assert spec.tier == 2
    assert any("WPAP" in stem for stem in spec.stems)


def test_czp_contributing_branch_tier2() -> None:
    spec = dispatch_environmental(
        _ctx(facts={"facts": {"wpap_type": "CZP", "zone_type": "contributing"}})
    )
    assert spec.branch_id == "environmental.edwards_czp"
    assert spec.tier == 2
    assert any("Contributing Zone" in stem for stem in spec.stems)


def test_outside_branch_tier1_with_cwqz() -> None:
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "outside",
                    "zone_type": "outside",
                    "waterway_name": "Cypress Creek",
                    "classification": "major",
                    "drainage_area_acres": 4237.5,
                    "cwqz_setback_ft": 300,
                    "source_fips": "48453",
                },
                **_EDWARDS_TCEQ_QUALITY,
            }
        )
    )
    assert spec.branch_id == "environmental.edwards_outside"
    assert spec.tier == 1
    assert spec.slots["cwqz_setback_ft"] == "300"
    assert any("300" in stem for stem in spec.stems)
    assert not any(m.name == "cwqz_setback_ft" for m in spec.missing_inputs)


def test_wpap_unknown_is_unclassified_not_outside() -> None:
    spec = dispatch_environmental(_ctx(facts={"facts": {"wpap_type": "unknown"}}))
    assert spec.branch_id == "environmental.edwards_unclassified"
    assert spec.tier == 2
    assert any("do NOT assert" in stem for stem in spec.stems)
    assert any(m.name == "edwards_aquifer_zone" for m in spec.missing_inputs)


def test_null_wpap_and_zone_is_unclassified() -> None:
    spec = dispatch_environmental(_ctx(facts={"facts": {"wpap_type": None, "zone_type": None}}))
    assert spec.branch_id == "environmental.edwards_unclassified"
    assert not any(
        "outside" in stem.lower() and "do not" not in stem.lower() for stem in spec.stems
    )


def test_outside_without_tceq_overlay_is_unclassified_not_tier1() -> None:
    """Bullick-class: inferred outside without edwards_overlay_tceq must not tier-1 assert."""
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "outside",
                    "zone_type": "outside",
                    "source_fips": "48453",
                },
                "quality": {"flags": ["terrain_3dep_complete", "waterway_overlay_nhd"]},
                "evidence": {
                    "zone_type": [
                        {
                            "source_id": "tcad",
                            "source_name": "County Appraisal District parcel record",
                        }
                    ]
                },
            }
        )
    )
    assert spec.branch_id == "environmental.edwards_unclassified"
    assert spec.tier == 2
    assert any("do NOT assert" in stem for stem in spec.stems)
    assert any(m.name == "edwards_aquifer_zone" for m in spec.missing_inputs)


def test_recharge_verification_maps_to_wpap() -> None:
    spec = dispatch_environmental(
        _ctx(facts={"facts": {"zone_type": "recharge_verification", "wpap_type": "WPAP"}})
    )
    assert spec.branch_id == "environmental.edwards_wpap"
    assert spec.tier == 2


def test_cwqz_null_outside_travis_is_not_gap() -> None:
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "outside",
                    "cwqz_setback_ft": None,
                    "source_fips": "48491",
                },
                **_EDWARDS_TCEQ_QUALITY,
            }
        )
    )
    assert spec.slots["in_travis_county"] == "false"
    assert not any(m.name == "cwqz_setback_ft" for m in spec.missing_inputs)
    assert any("not modeled outside Travis" in stem for stem in spec.stems)


def test_cwqz_minor_setback_100_not_legacy_50() -> None:
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "WPAP",
                    "waterway_name": "Skunk Hollow Creek",
                    "classification": "minor",
                    "cwqz_setback_ft": 100,
                    "source_fips": "48453",
                }
            }
        )
    )
    assert spec.slots["cwqz_setback_ft"] == "100"
    assert any("100" in stem for stem in spec.stems)
    assert any("50/100/200" in stem for stem in spec.stems)


def test_tier1_template_renders_outside_stem_and_cwqz() -> None:
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "outside",
                    "cwqz_setback_ft": 300,
                    "waterway_name": "Lockwood Creek",
                    "classification": "major",
                    "drainage_area_acres": 1536,
                    "source_fips": "48453",
                },
                **_EDWARDS_TCEQ_QUALITY,
            }
        )
    )
    output = render_environmental_tier1(spec)
    assert STEM_EA_OUTSIDE in output.suggested_language
    assert "300 feet" in output.suggested_language
    assert "Lockwood Creek" in output.suggested_language


def test_tcad_evidence_infers_travis_for_cwqz_without_source_fips() -> None:
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "outside",
                    "zone_type": "outside",
                    "waterway_name": "Cypress Creek",
                    "classification": "major",
                    "cwqz_setback_ft": 300,
                },
                "evidence": {
                    "waterway_name": [
                        {
                            "source_id": "tcad",
                            "source_name": "County Appraisal District parcel record",
                            "citation_url": "https://traviscad.org/propertysearch",
                        }
                    ],
                    "zone_type": [
                        {
                            "source_id": "tceq_edwards",
                            "source_name": "TCEQ Edwards Aquifer viewer",
                        }
                    ],
                },
            }
        )
    )
    assert spec.slots["source_fips"] == "48453"
    assert spec.slots["in_travis_county"] == "true"
    output = render_environmental_tier1(spec)
    assert "300 feet" in output.suggested_language
    assert "482.941" in output.suggested_language


def test_joseph_class_composite_watershed_cwqz_ehz() -> None:
    """Tier-1 outside + watershed/CWQZ/EHZ composite (Joseph Clayton class)."""
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "outside",
                    "zone_type": "outside",
                    "source_fips": "48453",
                    "cwqz_setback_ft": None,
                    "waterway_name": None,
                    "erosion_hazard": (
                        "Erosion hazard zone classification pending COA Erosion Hazard Zone "
                        "overlay assignment"
                    ),
                },
                "evidence": {
                    "zone_type": [
                        {
                            "source_id": "tceq_edwards",
                            "source_name": "TCEQ Edwards Aquifer viewer",
                        }
                    ]
                },
            },
            determinations={
                "determinations": [
                    {
                        "determination_id": "watershed_classification",
                        "inputs_used": {"watershed.watershed_name": "Walnut Creek-Colorado River"},
                    }
                ]
            },
        )
    )
    assert spec.branch_id == "environmental.edwards_outside"
    assert spec.tier == 1
    assert spec.slots["watershed_name"] == "Walnut Creek-Colorado River"
    assert spec.slots["in_travis_county"] == "true"
    assert any("Walnut Creek" in stem for stem in spec.stems)
    assert any("EHZ" in stem or "Erosion Hazard" in stem for stem in spec.stems)
    assert any(m.name == "erosion_hazard" for m in spec.missing_inputs)
    output = render_environmental_tier1(spec)
    assert STEM_EA_OUTSIDE in output.suggested_language
    assert "Walnut Creek" in output.suggested_language
    assert "Erosion Hazard Zone" in output.suggested_language
    assert "No jurisdictional waterway" in output.suggested_language


def test_cwqz_setback_suppresses_adjacent_waterway_contradiction() -> None:
    """Maha/Bullick class: resolved CWQZ must not contradict with 'no adjacent waterway'."""
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "outside",
                    "zone_type": "outside",
                    "waterway_name": "Maha Creek",
                    "classification": "major",
                    "drainage_area_acres": 8261,
                    "cwqz_setback_ft": 300,
                    "source_fips": "48453",
                },
                **_EDWARDS_TCEQ_QUALITY,
            },
            determinations={
                "determinations": [
                    {
                        "determination_id": "watershed_classification",
                        "inputs_used": {"watershed.watershed_name": "Maha Creek"},
                    }
                ]
            },
        )
    )
    assert any("300" in stem for stem in spec.stems)
    assert not any(
        "did not identify an adjacent jurisdictional waterway" in stem for stem in spec.stems
    )


def test_water_quality_and_waterway_distance_stems() -> None:
    spec = dispatch_environmental(
        _ctx(
            facts={
                "facts": {
                    "wpap_type": "outside",
                    "zone_type": "outside",
                    "source_fips": "48453",
                    "tceq_segment_id": "1428",
                    "water_quality_classification": "Exceptional",
                    "waterway_distance_ft": 420.0,
                    "cwqz_setback_applies": False,
                },
                **_EDWARDS_TCEQ_QUALITY,
            }
        )
    )
    assert spec.slots["tceq_segment_id"] == "1428"
    assert spec.slots["water_quality_classification"] == "Exceptional"
    assert any("TCEQ segment 1428" in stem for stem in spec.stems)
    assert any("420 ft" in stem for stem in spec.stems)
    assert any("CWQZ setback does not apply" in stem for stem in spec.stems)
