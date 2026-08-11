"""Tests for workbench field_context overlays on lake SectionContext."""

from __future__ import annotations

from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.field_overrides import apply_field_context_overrides


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
