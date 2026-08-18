"""Tests for workbench field_context overlays on lake SectionContext."""

from __future__ import annotations

from civilai_agent.pipeline.dispatch.descriptive import dispatch_descriptive
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.field_overrides import (
    apply_field_context_overrides,
    redact_unprompted_parcel_appraisal_facts,
    redact_unprompted_parcel_zoning_context,
    strip_zoning_dsi_from_field_context,
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


def _parcel_ctx_with_zoning_dsi() -> SectionContext:
    return SectionContext(
        entity_id="ent-1",
        section_id="parcel",
        facts={
            "facts": {
                "legal_desc": "AW0229 AW0229 - Foy, F. Sur., ACRES 27.43",
                "acreage": 27.43,
                "zoning_code": "MF-1",
                "ZONING_REGS": "MF-1 — Low-Density Multifamily",
                "MIN_LOT_SIZE": "12,000 sq ft",
                "SETBACKS": "Front: 20 ft; Side: 10 ft; Rear: 10 ft",
                "IMPERVIOUS_COVER_LIMIT": "50%",
            },
            "evidence": {
                "zoning_code": [
                    {
                        "source_name": "DSI",
                        "source_id": "georgetown",
                        "citation_url": "https://library.municode.com/tx/georgetown",
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
        determinations={
            "determinations": [
                {
                    "determination_id": "jurisdiction",
                    "conclusion": "Primary permitting authority: Georgetown",
                },
                {
                    "determination_id": "zoning_district",
                    "conclusion": (
                        "The property is zoned MF-1. Minimum lot size 12,000 sq ft; "
                        "impervious cover 50% per Georgetown LDC Section 11.02.010."
                    ),
                },
                {
                    "determination_id": "compliance_risk",
                    "conclusion": "moderate",
                },
            ]
        },
    )


def test_redact_parcel_zoning_dsi_when_absent_from_field_context() -> None:
    ctx = _parcel_ctx_with_zoning_dsi()
    field_context = {
        "PROPERTY_ADDRESS": "RR 2338, Georgetown, TX",
        "GOVERNING_JURIS": "Georgetown",
        "CAD_LEGAL_DESCRIPTION": "AW0229 AW0229 - Foy, F. Sur., ACRES 27.43",
        "COMPLIANCE_RISK": "moderate",
    }
    out = redact_unprompted_parcel_zoning_context(ctx, field_context)
    facts = out.facts["facts"]  # type: ignore[index]
    assert "zoning_code" not in facts
    assert "ZONING_REGS" not in facts
    assert "MIN_LOT_SIZE" not in facts
    assert "SETBACKS" not in facts
    assert "IMPERVIOUS_COVER_LIMIT" not in facts
    assert facts["legal_desc"] == "AW0229 AW0229 - Foy, F. Sur., ACRES 27.43"
    assert facts["acreage"] == 27.43
    evidence = out.facts["evidence"]  # type: ignore[index]
    assert "zoning_code" not in evidence
    assert "legal_desc" in evidence
    det_ids = [item["determination_id"] for item in out.determinations["determinations"]]  # type: ignore[index]
    assert "zoning_district" not in det_ids
    assert "jurisdiction" in det_ids
    assert "compliance_risk" in det_ids

    spec = dispatch_descriptive(out, "parcel")
    assert not any(c.get("field") == "zoning_code" for c in spec.citations)
    assert not any(
        item.get("determination_id") == "zoning_district" for item in spec.determinations
    )


def test_redact_keeps_zoning_when_zoning_regs_in_field_context() -> None:
    ctx = _parcel_ctx_with_zoning_dsi()
    out = redact_unprompted_parcel_zoning_context(
        ctx,
        {"ZONING_REGS": "MF-1 — Low-Density Multifamily"},
    )
    facts = out.facts["facts"]  # type: ignore[index]
    assert facts["zoning_code"] == "MF-1"
    assert facts["MIN_LOT_SIZE"] == "12,000 sq ft"
    det_ids = [item["determination_id"] for item in out.determinations["determinations"]]  # type: ignore[index]
    assert "zoning_district" in det_ids


def test_redact_zoning_skips_non_parcel_sections() -> None:
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="access",
        facts={"facts": {"zoning_code": "MF-1", "MIN_LOT_SIZE": "12,000 sq ft"}},
        determinations={
            "determinations": [{"determination_id": "zoning_district", "conclusion": "MF-1"}]
        },
    )
    out = redact_unprompted_parcel_zoning_context(ctx, {})
    assert out.facts["facts"]["zoning_code"] == "MF-1"  # type: ignore[index]
    assert out.determinations["determinations"][0]["determination_id"] == "zoning_district"  # type: ignore[index]


def test_strip_zoning_dsi_from_parcel_field_context() -> None:
    stripped = strip_zoning_dsi_from_field_context(
        {
            "PROPERTY_ADDRESS": "RR 2338, Georgetown, TX",
            "GOVERNING_JURIS": "Georgetown",
            "MIN_LOT_SIZE": "12,000 sq ft",
            "SETBACKS": "Front: 20 ft",
            "ZONING_REGS": "MF-1",
            "ZONING_ANALYSIS_BASIS": "proposed",
        },
        "parcel",
    )
    assert stripped == {
        "PROPERTY_ADDRESS": "RR 2338, Georgetown, TX",
        "GOVERNING_JURIS": "Georgetown",
    }


def test_strip_zoning_dsi_keeps_codes_on_zoning_section() -> None:
    ctx = {
        "ZONING_REGS": "MF-1",
        "MIN_LOT_SIZE": "12,000 sq ft",
    }
    assert strip_zoning_dsi_from_field_context(ctx, "zoning") == ctx
