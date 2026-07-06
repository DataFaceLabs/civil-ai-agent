"""Tests for pipeline run wiring (S3.3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import (
    AgentWorkflow,
    WorkbenchContext,
)
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.run import run_section_draft


def _zoning_det(**inputs: object) -> dict[str, object]:
    return {
        "determinations": [
            {
                "determination_id": "zoning_district",
                "inputs_used": inputs,
            }
        ]
    }


def _context(section_id: str = "zoning") -> WorkbenchContext:
    return WorkbenchContext(
        project_id="test",
        entity_id="ent-1",
        active_section_id=section_id,
        workflow=AgentWorkflow.SECTION_DRAFT,
        request="Draft section.",
    )


def test_zoning_county_uses_template_path() -> None:
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="zoning",
        facts={"facts": {"zoning_code": None, "allowed_use_flags": "[]"}},
        determinations=_zoning_det(
            **{
                "jurisdiction.jurisdiction_primary": "Travis County",
                "jurisdiction.review_track": "county_baseline",
            }
        ),
    )

    with patch("civilai_agent.pipeline.run.fetch_section_context", return_value=ctx):
        response = run_section_draft(_context(), dry_run=False)

    assert response.artifacts
    assert response.artifacts[0].metadata["pipeline_path"] == "template"
    assert response.artifacts[0].metadata["branch_id"] == "zoning.county_no_zoning"
    assert "not subject to zoning regulations" in response.message


def test_zoning_tier2_dry_run_uses_render_path_not_legacy() -> None:
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="zoning",
        facts={
            "facts": {
                "zoning_code": "CS",
                "zoning_base": "Commercial Services",
                "allowed_use_flags": "[]",
            }
        },
        determinations=_zoning_det(
            **{
                "jurisdiction.jurisdiction_primary": "City of Austin",
                "jurisdiction.in_city_limits": True,
            }
        ),
    )

    with patch("civilai_agent.pipeline.run.fetch_section_context", return_value=ctx):
        response = run_section_draft(_context(), dry_run=True)

    assert "[pipeline dry-run] would render zoning" in response.message
    assert response.artifacts[0].metadata["pipeline_path"] == "render"
    assert response.artifacts[0].metadata["branch_id"] == "zoning.zoned_city"
    assert "Would invoke agent" not in response.message


@patch("civilai_agent.pipeline.render.render_draft")
def test_zoning_tier2_live_calls_renderer(mock_render: MagicMock) -> None:
    mock_render.return_value = SectionDraftOutput(
        suggested_language="The property is zoned CS (Commercial Services)."
    )
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="zoning",
        facts={"facts": {"zoning_code": "CS", "allowed_use_flags": "[]"}},
        determinations=_zoning_det(
            **{
                "jurisdiction.jurisdiction_primary": "City of Austin",
                "jurisdiction.in_city_limits": True,
            }
        ),
    )

    with patch("civilai_agent.pipeline.run.fetch_section_context", return_value=ctx):
        response = run_section_draft(_context(), dry_run=False)

    mock_render.assert_called_once()
    assert response.artifacts[0].metadata["pipeline_path"] == "render"
    assert "CS" in response.message


@patch("civilai_agent.pipeline.templates.environmental.render_environmental_tier1")
@patch("civilai_agent.pipeline.dispatch.environmental.dispatch_environmental")
@patch("civilai_agent.pipeline.run.fetch_section_context")
def test_environmental_uses_pipeline_not_legacy(
    mock_fetch: MagicMock,
    mock_dispatch: MagicMock,
    mock_template: MagicMock,
) -> None:
    from civilai_agent.guardrails.structured import SectionDraftOutput
    from civilai_agent.pipeline.specs import DraftSpec

    ctx = SectionContext(
        entity_id="ent-1",
        section_id="environmental",
        facts={"facts": {"wpap_type": "outside", "cwqz_setback_ft": None}},
    )
    mock_fetch.return_value = ctx
    mock_dispatch.return_value = DraftSpec(
        entity_id="ent-1",
        section_id="environmental",
        branch_id="environmental.edwards_outside",
        tier=1,
    )
    mock_template.return_value = SectionDraftOutput(
        suggested_language="Outside Edwards Aquifer.",
        caveats=(),
        verification_steps=(),
        data_gaps=(),
        sources=(),
    )

    response = run_section_draft(_context(section_id="environmental"), dry_run=False)

    mock_dispatch.assert_called_once()
    mock_template.assert_called_once()
    assert response.artifacts[0].metadata["pipeline_path"] == "template"
