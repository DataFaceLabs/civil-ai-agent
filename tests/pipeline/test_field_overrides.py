"""Tests for workbench field_context overlays on lake SectionContext."""

from __future__ import annotations

from civilai_agent.pipeline.dispatch.descriptive import dispatch_descriptive
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.field_overrides import (
    apply_field_context_overrides,
    redact_unprompted_parcel_appraisal_facts,
)


def test_apply_field_context_overrides_replaces_stale_etj_jurisdiction() -> None:
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="parcel",
        facts={
            "facts": {
                "property_acres": "12.4",
                "jurisdiction_primary": "City of Georgetown (ETJ)",
            }
        },
        determinations={
            "determinations": [
                {
                    "determination_id": "jurisdiction",
                    "conclusion": (
                        "The property is located in Williamson County within the City of "
                        "Georgetown extraterritorial jurisdiction (ETJ)."
                    ),
                    "inputs_used": {
                        "jurisdiction.jurisdiction_primary": "City of Georgetown (ETJ)",
                        "jurisdiction.in_etj": True,
                        "jurisdiction.in_city_limits": False,
                    },
                }
            ]
        },
    )

    out = apply_field_context_overrides(
        ctx,
        {
            "GOVERNING_JURIS": "City of Georgetown, Williamson County",
            "PERMITTING_AUTHORITY_DETAIL": (
                "Primary permitting authority: City of Georgetown; "
                "county coordination: Williamson County"
            ),
        },
    )

    assert out is not ctx
    facts = out.facts["facts"] if isinstance(out.facts, dict) else {}
    assert facts["jurisdiction_primary"] == "City of Georgetown, Williamson County"
    assert facts["GOVERNING_JURIS"] == "City of Georgetown, Williamson County"

    det = out.determinations["determinations"][0]  # type: ignore[index]
    assert "extraterritorial" not in str(det["conclusion"]).lower()
    assert "City of Georgetown, Williamson County" in str(det["conclusion"])
    inputs = det["inputs_used"]
    assert inputs["jurisdiction.jurisdiction_primary"] == ("City of Georgetown, Williamson County")
    assert inputs["jurisdiction.in_etj"] is False
    assert inputs["jurisdiction.in_city_limits"] is True


def test_apply_field_context_overrides_noop_without_jurisdiction_fields() -> None:
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="parcel",
        facts={"facts": {"jurisdiction_primary": "City of Georgetown (ETJ)"}},
    )
    out = apply_field_context_overrides(ctx, {"PROPERTY_ADDRESS": "100 Main St"})
    assert out.facts["facts"]["PROPERTY_ADDRESS"] == "100 Main St"  # type: ignore[index]
    assert out.facts["facts"]["jurisdiction_primary"] == "City of Georgetown (ETJ)"  # type: ignore[index]
    assert out.facts["facts"]["property_address"] == "100 Main St"  # type: ignore[index]


def _parcel_ctx_with_appraisal() -> SectionContext:
    return SectionContext(
        entity_id="ent-1",
        section_id="parcel",
        facts={
            "facts": {
                "legal_desc": "AW0229 AW0229 - Foy, F. Sur., ACRES 27.43",
                "market_value_usd": 3797757,
                "land_value_usd": 3763780,
                "improvement_value_usd": 33977,
                "living_area_sqft": 922,
                "acreage": 27.43,
            },
            "evidence": {
                "market_value_usd": [
                    {
                        "source_name": "WCAD",
                        "source_id": "wcad",
                        "citation_url": "https://example.com/cad",
                    }
                ],
                "legal_desc": [
                    {
                        "source_name": "WCAD",
                        "source_id": "wcad",
                        "citation_url": "https://example.com/legal",
                    }
                ],
            },
        },
    )


def test_redact_parcel_appraisal_facts_when_absent_from_field_context() -> None:
    ctx = _parcel_ctx_with_appraisal()
    field_context = {
        "PROPERTY_ADDRESS": "RR 2338, Georgetown, TX 78633",
        "CAD_LEGAL_DESCRIPTION": "AW0229 AW0229 - Foy, F. Sur., ACRES 27.43",
        "ZONING_REGS": "MF-1 — Low-Density Multifamily",
    }
    out = redact_unprompted_parcel_appraisal_facts(ctx, field_context)
    facts = out.facts["facts"]  # type: ignore[index]
    assert "market_value_usd" not in facts
    assert "land_value_usd" not in facts
    assert "improvement_value_usd" not in facts
    assert "living_area_sqft" not in facts
    assert facts["legal_desc"] == "AW0229 AW0229 - Foy, F. Sur., ACRES 27.43"
    assert facts["acreage"] == 27.43
    evidence = out.facts["evidence"]  # type: ignore[index]
    assert "market_value_usd" not in evidence
    assert "legal_desc" in evidence

    spec = dispatch_descriptive(out, "parcel")
    assert not any(c.get("field") == "market_value_usd" for c in spec.citations)


def test_redact_keeps_valuation_when_cad_valuation_in_field_context() -> None:
    ctx = _parcel_ctx_with_appraisal()
    out = redact_unprompted_parcel_appraisal_facts(
        ctx,
        {"CAD_VALUATION": "Market value: $3,797,757, Land value: $3,763,780"},
    )
    facts = out.facts["facts"]  # type: ignore[index]
    assert facts["market_value_usd"] == 3797757
    assert facts["land_value_usd"] == 3763780
    assert facts["improvement_value_usd"] == 33977
    assert "living_area_sqft" not in facts


def test_redact_keeps_living_area_when_building_detail_in_field_context() -> None:
    ctx = _parcel_ctx_with_appraisal()
    out = redact_unprompted_parcel_appraisal_facts(
        ctx,
        {"BUILDING_DETAIL": "Living area: 922 sqft"},
    )
    facts = out.facts["facts"]  # type: ignore[index]
    assert facts["living_area_sqft"] == 922
    assert "market_value_usd" not in facts
    assert "land_value_usd" not in facts
    assert "improvement_value_usd" not in facts


def test_redact_keeps_only_lake_keys_present_in_field_context() -> None:
    ctx = _parcel_ctx_with_appraisal()
    out = redact_unprompted_parcel_appraisal_facts(
        ctx,
        {"living_area_sqft": "922"},
    )
    facts = out.facts["facts"]  # type: ignore[index]
    assert facts["living_area_sqft"] == 922
    assert "market_value_usd" not in facts


def test_redact_ignores_empty_allow_codes() -> None:
    ctx = _parcel_ctx_with_appraisal()
    out = redact_unprompted_parcel_appraisal_facts(ctx, {"CAD_VALUATION": "  "})
    facts = out.facts["facts"]  # type: ignore[index]
    assert "market_value_usd" not in facts


def test_redact_skips_non_parcel_sections() -> None:
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="access",
        facts={"facts": {"market_value_usd": 1, "living_area_sqft": 2}},
    )
    out = redact_unprompted_parcel_appraisal_facts(ctx, {})
    assert out.facts["facts"]["market_value_usd"] == 1  # type: ignore[index]
    assert out.facts["facts"]["living_area_sqft"] == 2  # type: ignore[index]
