"""Tests for flood pipeline run wiring (S4.1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.run import run_section_draft


def _context() -> WorkbenchContext:
    return WorkbenchContext(
        project_id="test",
        entity_id="ent-1",
        active_section_id="flood",
        workflow=AgentWorkflow.SECTION_DRAFT,
        request="Draft section.",
    )


def test_flood_zone_x_uses_template_path() -> None:
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="flood",
        facts={
            "facts": {
                "fema_zone": "X",
                "floodway_flag": False,
                "panel_id": None,
                "effective_date": None,
            },
            "evidence": {
                "fema_zone": [{"source_record_id": "48453C_2244"}],
            },
        },
    )

    with patch("civilai_agent.pipeline.run.fetch_section_context", return_value=ctx):
        response = run_section_draft(_context(), dry_run=False)

    assert response.artifacts
    assert response.artifacts[0].metadata["pipeline_path"] == "template"
    assert response.artifacts[0].metadata["branch_id"] == "flood.zone_x"
    assert "zone x" in response.message.lower()


@patch("civilai_agent.pipeline.render.render_draft")
def test_flood_sfha_live_calls_renderer(mock_render: MagicMock) -> None:
    mock_render.return_value = SectionDraftOutput(
        suggested_language="The property lies within FEMA Zone AE."
    )
    ctx = SectionContext(
        entity_id="ent-1",
        section_id="flood",
        facts={"facts": {"fema_zone": "AE", "floodway_flag": False}},
    )

    with patch("civilai_agent.pipeline.run.fetch_section_context", return_value=ctx):
        response = run_section_draft(_context(), dry_run=False)

    mock_render.assert_called_once()
    assert response.artifacts[0].metadata["pipeline_path"] == "render"
    assert response.artifacts[0].metadata["branch_id"] == "flood.sfha"
