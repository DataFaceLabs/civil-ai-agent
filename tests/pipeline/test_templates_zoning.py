"""Tests for zoning Tier-0 templates (S3.2)."""

from __future__ import annotations

from civilai_agent.pipeline.dispatch.zoning import dispatch_zoning
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.specs import DraftSpec
from civilai_agent.pipeline.templates.zoning import render_zoning_tier0
from civilai_agent.pipeline.validate import fact_echo_warnings


def _zoning_det(**inputs: object) -> dict[str, object]:
    return {
        "determinations": [
            {
                "determination_id": "zoning_district",
                "inputs_used": inputs,
            }
        ]
    }


def test_county_template_renders_stem_b() -> None:
    spec = dispatch_zoning(
        SectionContext(
            entity_id="ent-hudson",
            section_id="zoning",
            facts={"facts": {"zoning_code": None, "allowed_use_flags": "[]"}},
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "Travis County",
                    "jurisdiction.review_track": "county_baseline",
                }
            ),
        )
    )
    output = render_zoning_tier0(spec)
    assert "Travis County" in output.suggested_language
    assert "not subject to zoning regulations" in output.suggested_language
    assert output.caveats
    assert any("overlay" in step.lower() for step in output.verification_steps)


def test_etj_template_renders_stem_c() -> None:
    spec = dispatch_zoning(
        SectionContext(
            entity_id="ent-cresthill",
            section_id="zoning",
            facts={"facts": {"zoning_code": None, "allowed_use_flags": "[]"}},
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "City of Kyle (ETJ)",
                    "jurisdiction.in_etj": True,
                }
            ),
        )
    )
    output = render_zoning_tier0(spec)
    assert "City of Kyle" in output.suggested_language
    assert "no zoning district" in output.suggested_language
    assert any("ETJ" in step for step in output.verification_steps)


def test_fact_echo_passes_on_county_template_by_construction() -> None:
    spec = DraftSpec(
        entity_id="ent-1",
        section_id="zoning",
        branch_id="zoning.county_no_zoning",
        tier=0,
        slots={"jurisdiction_primary": "Travis County", "zoning_code": None},
        stems=["county stem"],
    )
    output = render_zoning_tier0(spec)
    assert fact_echo_warnings(spec, output) == ()


def test_fact_echo_passes_on_etj_template_by_construction() -> None:
    spec = DraftSpec(
        entity_id="ent-1",
        section_id="zoning",
        branch_id="zoning.etj",
        tier=0,
        slots={"jurisdiction_primary": "City of Kyle (ETJ)", "zoning_code": None},
        stems=["etj stem"],
    )
    output = render_zoning_tier0(spec)
    assert fact_echo_warnings(spec, output) == ()


def test_rejects_non_tier0_branch() -> None:
    spec = DraftSpec(
        entity_id="ent-1",
        section_id="zoning",
        branch_id="zoning.zoned_city",
        tier=2,
        slots={"zoning_code": "CS"},
    )
    try:
        render_zoning_tier0(spec)
    except ValueError as exc:
        assert "No Tier-0 template" in str(exc)
    else:
        raise AssertionError("expected ValueError")
