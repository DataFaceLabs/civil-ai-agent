"""Tests for zoning rails tools and analysisBasis field overlay."""

from __future__ import annotations

import json

from civilai_agent.tools.zoning_rails import (
    apply_analysis_basis_to_field_context,
    get_zoning_comparisons,
    get_zoning_rails,
    set_zoning_scenario,
)


def _scenario(*, basis: str = "proposed", status: str = "computed") -> dict:
    return {
        "analysis_basis": basis,
        "active_scenario_id": "sc-1",
        "baseline_jurisdiction_key": "coa_full",
        "effective_jurisdiction_key": "coa_full",
        "scenarios": [
            {
                "scenario_id": "sc-1",
                "label": "Rezone to MF-4",
                "status": status,
                "proposed": {
                    "fields": {
                        "ZONING_REGS": {
                            "value": "Proposed MF-4: LDC §25-2-492 excerpt",
                            "origin": "regtext",
                        }
                    }
                },
                "comparisons": [
                    {
                        "fe_code": "ZONING_REGS",
                        "diff": {"kind": "changed", "summary": "Changed"},
                        "risk": {"level": "medium", "drivers": ["entitlement_rezoning_required"]},
                        "evidence": [
                            {
                                "citation": "LDC §25-2-492",
                                "deep_link": "https://example.com",
                                "excerpt": "MF-4 allows multifamily.",
                            }
                        ],
                    }
                ],
                "risk_summary": {"overall": "medium"},
            }
        ],
    }


def test_apply_analysis_basis_overlays_proposed_fields() -> None:
    merged = apply_analysis_basis_to_field_context(
        {"ZONING_REGS": "SF-2"},
        _scenario(),
    )
    assert "MF-4" in merged["ZONING_REGS"]
    assert merged["ZONING_ANALYSIS_BASIS"] == "proposed"


def test_apply_analysis_basis_ignores_draft() -> None:
    merged = apply_analysis_basis_to_field_context(
        {"ZONING_REGS": "SF-2"},
        _scenario(status="draft"),
    )
    assert merged["ZONING_REGS"] == "SF-2"


def test_get_zoning_tools_return_json() -> None:
    set_zoning_scenario(_scenario())
    rails = json.loads(get_zoning_rails())
    assert rails["has_scenario"] is True
    assert rails["analysis_basis"] == "proposed"
    comps = json.loads(get_zoning_comparisons())
    assert comps["comparisons"]
    assert comps["comparisons"][0]["evidence"][0]["citation"] == "LDC §25-2-492"
    set_zoning_scenario(None)
