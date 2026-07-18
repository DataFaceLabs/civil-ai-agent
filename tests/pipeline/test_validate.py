"""Tests for pipeline fact-echo validator (S2.2)."""

from __future__ import annotations

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.pipeline.specs import DraftSpec
from civilai_agent.pipeline.validate import fact_echo_warnings


def _output(language: str) -> SectionDraftOutput:
    return SectionDraftOutput(suggested_language=language)


def _spec(**kwargs) -> DraftSpec:
    defaults = {
        "entity_id": "ent-1",
        "section_id": "zoning",
        "branch_id": "zoning.zoned_city",
        "tier": 2,
    }
    defaults.update(kwargs)
    return DraftSpec(**defaults)


# --- zoning ---


def test_zoning_warns_when_code_present_and_draft_denies_zoning() -> None:
    spec = _spec(section_id="zoning", slots={"zoning_code": "DR"})
    output = _output("This property is not subject to zoning regulations.")
    warnings = fact_echo_warnings(spec, output)
    assert len(warnings) == 1
    assert "zoning_code" in warnings[0]


def test_zoning_benign_overlay_phrase_does_not_warn() -> None:
    spec = _spec(section_id="zoning", slots={"zoning_code": "DR"})
    output = _output("No zoning overlays were identified for this parcel.")
    assert fact_echo_warnings(spec, output) == ()


def test_zoning_no_warning_when_code_absent() -> None:
    spec = _spec(section_id="zoning", slots={"zoning_code": None})
    output = _output("No zoning applies to this county parcel.")
    assert fact_echo_warnings(spec, output) == ()


# --- flood ---


def test_flood_warns_sfha_zone_with_outside_assertion() -> None:
    spec = _spec(
        section_id="flood",
        branch_id="flood.zone_ae",
        slots={"flood_zone": "AE"},
    )
    output = _output("The tract is not in the 100-year floodplain.")
    warnings = fact_echo_warnings(spec, output)
    assert len(warnings) == 1
    assert "SFHA" in warnings[0]


def test_flood_warns_non_sfha_with_inside_assertion() -> None:
    spec = _spec(
        section_id="flood",
        branch_id="flood.zone_x",
        slots={"flood_zone": "X"},
    )
    output = _output("The property is in the 100-year floodplain.")
    warnings = fact_echo_warnings(spec, output)
    assert len(warnings) == 1
    assert "non-SFHA" in warnings[0]


def test_flood_no_warning_when_sfha_and_consistent() -> None:
    spec = _spec(
        section_id="flood",
        branch_id="flood.zone_ae",
        slots={"flood_zone": "AE"},
    )
    output = _output("The tract lies within Zone AE in the Special Flood Hazard Area.")
    assert fact_echo_warnings(spec, output) == ()


# --- utilities ---


def test_utilities_warns_availability_without_coverage_qualifier() -> None:
    spec = _spec(
        section_id="utilities",
        branch_id="utilities.public_main",
        slots={"water_provider": "City of Austin"},
    )
    output = _output("Municipal water is available at the site frontage.")
    warnings = fact_echo_warnings(spec, output)
    assert len(warnings) == 1
    assert "coverage qualifier" in warnings[0]


def test_utilities_warns_when_ossf_branch_but_draft_denies_ossf() -> None:
    spec = _spec(
        section_id="utilities",
        branch_id="utilities.provider_distant",
        slots={"ww_main_distance_ft": "1137"},
    )
    output = _output("The property is not required to install an on-site sewage facility (OSSF).")
    warnings = fact_echo_warnings(spec, output)
    assert len(warnings) == 1
    assert "OSSF" in warnings[0]


def test_utilities_no_warning_with_coverage_language() -> None:
    spec = _spec(
        section_id="utilities",
        branch_id="utilities.public_main",
        slots={"water_provider": "City of Austin"},
    )
    output = _output(
        "Water service territory coverage includes the parcel; capacity is not confirmed."
    )
    assert fact_echo_warnings(spec, output) == ()


def test_utilities_no_warning_when_capacity_fact_present() -> None:
    spec = _spec(
        section_id="utilities",
        branch_id="utilities.public_main",
        slots={"water_provider": "City of Austin", "capacity_confirmed": "true"},
    )
    output = _output("Municipal water is available at the site.")
    assert fact_echo_warnings(spec, output) == ()


def test_non_matching_section_returns_no_warnings() -> None:
    spec = _spec(section_id="topography", branch_id="topo.flat")
    output = _output("The parcel is outside the Edwards Aquifer recharge zone.")
    assert fact_echo_warnings(spec, output) == ()


def test_environmental_warns_when_unclassified_branch_asserts_outside() -> None:
    spec = _spec(
        section_id="environmental",
        branch_id="environmental.edwards_unclassified",
        slots={"wpap_type": "outside", "zone_type": "outside"},
    )
    output = _output(
        "This site is located outside the Edwards Aquifer Transition Zone; "
        "no additional permits are required."
    )
    warnings = fact_echo_warnings(spec, output)
    assert len(warnings) == 1
    assert "Edwards Aquifer" in warnings[0]
