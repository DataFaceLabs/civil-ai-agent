"""Contract tests for utilities branch dispatcher (S5.2)."""

from __future__ import annotations

import pytest

from civilai_agent.pipeline.dispatch.utilities import dispatch_utilities
from civilai_agent.pipeline.fetch import SectionContext


def test_public_main_branch_when_centralized_sewer() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": False,
                    "water_provider": "Austin Water",
                    "wastewater_provider": "Austin Water Wastewater",
                    "ww_main_distance_ft": 50,
                },
                "quality": {
                    "flags": [
                        "water_ccn_overlay_observed",
                        "wastewater_ccn_overlay_observed",
                    ]
                },
            },
        )
    )
    assert spec.branch_id == "utilities.public_main"
    assert spec.tier == 2
    assert "coverage" in spec.stems[0].lower()


def test_public_main_from_lake_nearest_wastewater_meters() -> None:
    """Lake serves nearest_*_distance_m; dispatch must convert to ft (not miss the field)."""
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": False,
                    "water_provider": "Austin Water",
                    "wastewater_provider": "Austin Water Wastewater",
                    "nearest_wastewater_distance_m": 15.24,  # ~50 ft
                    "nearest_water_distance_m": 12.0,
                    "network_coverage_tier": "line_gis",
                },
                "quality": {
                    "flags": [
                        "water_ccn_overlay_observed",
                        "wastewater_ccn_overlay_observed",
                    ]
                },
            },
        )
    )
    assert spec.branch_id == "utilities.public_main"
    assert float(spec.slots["ww_main_distance_ft"] or 0) == pytest.approx(50.0, rel=1e-3)
    assert any("proximity" in stem.lower() for stem in spec.stems)


def test_gis_viewer_citations_and_stems_from_drawing_href() -> None:
    viewer = (
        "https://www.arcgis.com/apps/mapviewer/index.html"
        "?url=https%3A%2F%2Fexample%2FMapServer%2F25&center=-97.7,30.2"
    )
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": False,
                    "water_provider": "Austin Water",
                    "wastewater_provider": "Austin Water Wastewater",
                    "ww_main_distance_ft": 50,
                    "nearest_water_drawing_href": viewer,
                },
                "quality": {
                    "flags": [
                        "water_ccn_overlay_observed",
                        "wastewater_ccn_overlay_observed",
                    ]
                },
            },
        )
    )
    assert any(
        c.get("url") == viewer and c.get("source_name") == "Nearest water main"
        for c in spec.citations
    )
    assert any(f"[Nearest water main]({viewer})" in stem for stem in spec.stems)


def test_provider_distant_branch() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": False,
                    "wastewater_provider": "Austin Water Wastewater",
                    "ww_main_distance_ft": 1137,
                }
            },
        )
    )
    assert spec.branch_id == "utilities.provider_distant"
    assert any("SER" in stem for stem in spec.stems)


def test_ossf_branch_when_required() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": True,
                    "ossf_authority": "Travis County",
                }
            },
        )
    )
    assert spec.branch_id == "utilities.ossf"
    assert any("OSSF" in stem or "septic" in stem.lower() for stem in spec.stems)


def test_no_provider_falls_through_to_ossf() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={"facts": {"ossf_required": None, "wastewater_provider": None}},
        )
    )
    assert spec.branch_id == "utilities.ossf"


def test_ww_distance_gap_when_provider_without_distance() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": False,
                    "wastewater_provider": "City of Round Rock",
                }
            },
        )
    )
    assert any(m.name == "ww_main_distance_ft" for m in spec.missing_inputs)


def test_power_provider_stem_prevents_austin_energy_default() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": True,
                    "power_provider": "PEDERNALES ELECTRIC COOP, INC",
                },
                "quality": {"flags": ["electric_ccn_overlay_observed"]},
            },
        )
    )
    assert spec.slots["power_provider"] == "PEDERNALES ELECTRIC COOP, INC"
    assert any("PEDERNALES" in stem for stem in spec.stems)
    assert any("Do not default to Austin Energy" in stem for stem in spec.stems)


def test_ossf_lot_size_determination_wired_when_ossf_branch() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": True,
                    "ossf_authority": "Travis County",
                }
            },
            determinations={
                "determinations": [
                    {
                        "determination_id": "ossf_lot_size_feasibility",
                        "conclusion": (
                            "The property (0.85 ac) is below the 1.0-acre minimum for an "
                            "on-site sewage facility."
                        ),
                    }
                ]
            },
        )
    )
    assert spec.branch_id == "utilities.ossf"
    assert any(
        item.get("determination_id") == "ossf_lot_size_feasibility" for item in spec.determinations
    )
    assert any("OSSF lot-size feasibility" in stem for stem in spec.stems)
    assert any("0.85 ac" in stem for stem in spec.stems)


def test_unconfirmed_ccn_clears_provider_slots() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": True,
                    "power_provider": "AUSTIN ENERGY",
                },
                "quality": {"flags": ["electric_baseline_inference"]},
            },
        )
    )
    assert spec.slots["power_provider"] is None
    assert any("not name a provider" in stem.lower() for stem in spec.stems)


def test_distant_main_blocks_ossf_not_required_claim() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": False,
                    "wastewater_provider": "Austin Water Wastewater",
                    "ww_main_distance_ft": 1137,
                },
                "quality": {"flags": ["wastewater_ccn_overlay_observed"]},
            },
        )
    )
    assert spec.branch_id == "utilities.provider_distant"
    assert any("Do NOT state that centralized sewer is available" in stem for stem in spec.stems)


def test_nearest_main_diameter_material_slots_and_stems() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": False,
                    "water_provider": "Austin Water",
                    "wastewater_provider": "Austin Water Wastewater",
                    "nearest_water_distance_m": 0.0,
                    "nearest_water_diameter_in": 8.0,
                    "nearest_water_material": "DI",
                    "network_coverage_tier": "line_gis",
                },
                "quality": {
                    "flags": [
                        "water_ccn_overlay_observed",
                        "wastewater_ccn_overlay_observed",
                    ]
                },
            },
        )
    )
    assert spec.slots["nearest_water_diameter_in"] == "8.0"
    assert spec.slots["nearest_water_material"] == "DI"
    assert any("8 in diameter" in stem and "DI" in stem for stem in spec.stems)


def test_tap_cards_narrative_and_docuware_citation() -> None:
    href = "https://docuware.example/tap/226978"
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {
                    "ossf_required": False,
                    "wastewater_provider": "Austin Water Wastewater",
                    "ww_main_distance_ft": 50,
                    "tap_cards_json": [
                        {
                            "address_label": "123 Bonnie Rd",
                            "utility_type": "WWT",
                            "document_href": href,
                        }
                    ],
                },
                "quality": {"flags": ["wastewater_ccn_overlay_observed"]},
            },
        )
    )
    assert any("1 municipal tap card" in stem for stem in spec.stems)
    assert any("historical connection" in stem.lower() for stem in spec.stems)
    assert any(c.get("url") == href and "WWT" in str(c.get("source_name")) for c in spec.citations)


def test_evidence_as_of_passes_into_citations() -> None:
    spec = dispatch_utilities(
        SectionContext(
            entity_id="ent-1",
            section_id="utilities",
            facts={
                "facts": {"ossf_required": True},
                "evidence": {
                    "ossf_required": [
                        {
                            "source_name": "Lake",
                            "source_id": "tcad",
                            "citation_url": "https://example.com/src",
                            "as_of": "2026-07-02",
                        }
                    ]
                },
            },
        )
    )
    assert any(c.get("as_of") == "2026-07-02" for c in spec.citations)
