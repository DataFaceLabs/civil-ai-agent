"""Descriptive-section pipeline (parcel, access) + token telemetry wiring.

Migrating parcel/access off the legacy tool loop (~16-18k input tok/draft) onto the
single-render pipeline path (~3-5k) is the cost win from consolidating the last legacy
sections. These assert the routing, that the tenant format/system prompt is threaded, and
that token telemetry is surfaced (the pipeline previously reported zero tokens).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
from civilai_agent.pipeline.dispatch.descriptive import dispatch_descriptive
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.render import RenderResult
from civilai_agent.pipeline.run import run_section_draft


def _ctx(section_id: str) -> SectionContext:
    return SectionContext(
        entity_id="ent-1",
        section_id=section_id,
        facts={
            "facts": {"property_acres": "1.88", "cad_land_use": "F3"},
            "evidence": {
                "property_acres": [
                    {"citation_url": "https://tcad.example/x", "source_name": "TCAD"}
                ]
            },
        },
        determinations={
            "determinations": [{"determination_id": "compliance_risk", "conclusion": "moderate"}]
        },
    )


def _context(section_id: str) -> WorkbenchContext:
    return WorkbenchContext(
        project_id="test",
        entity_id="ent-1",
        active_section_id=section_id,
        workflow=AgentWorkflow.SECTION_DRAFT,
        request="Draft the section.",
        system_prompt="Format: h1 and h2 headings.",
    )


def test_dispatch_descriptive_packs_facts_citations_determinations() -> None:
    spec = dispatch_descriptive(_ctx("parcel"), "parcel")
    assert spec.section_id == "parcel"
    assert spec.branch_id == "parcel.render"
    assert spec.facts["facts"]["property_acres"] == "1.88"
    assert spec.citations and spec.citations[0]["url"] == "https://tcad.example/x"
    assert spec.determinations and spec.determinations[0]["determination_id"] == "compliance_risk"
    assert spec.stems == []  # descriptive sections carry no branch/stem logic


@pytest.mark.parametrize("section_id", ["parcel", "access"])
@patch("civilai_agent.pipeline.render.render_draft")
def test_descriptive_sections_use_render_pipeline_not_legacy(
    mock_render: MagicMock, section_id: str
) -> None:
    mock_render.return_value = RenderResult(
        output=SectionDraftOutput(
            suggested_language=f"# {section_id.title()}\n\n## Subsection\nText."
        ),
        input_tokens=4200,
        output_tokens=1100,
        model_id="haiku",
    )
    with patch("civilai_agent.pipeline.run.fetch_section_context", return_value=_ctx(section_id)):
        response = run_section_draft(_context(section_id), dry_run=False)

    mock_render.assert_called_once()
    artifact = response.artifacts[0]
    assert artifact.metadata["pipeline_path"] == "render"
    assert artifact.metadata["branch_id"] == f"{section_id}.render"
    # Telemetry surfaced (pipeline previously reported 0 tokens).
    assert response.trace_summary.input_tokens == 4200
    assert response.trace_summary.output_tokens == 1100
    # Tenant format directive + system prompt threaded through for good formatting.
    assert mock_render.call_args.kwargs["tenant_system_prompt"] == "Format: h1 and h2 headings."


@patch("civilai_agent.pipeline.render.render_draft")
def test_descriptive_dry_run_does_not_call_renderer(mock_render: MagicMock) -> None:
    with patch("civilai_agent.pipeline.run.fetch_section_context", return_value=_ctx("parcel")):
        response = run_section_draft(_context("parcel"), dry_run=True)

    mock_render.assert_not_called()
    assert "[pipeline dry-run] would render parcel" in response.message
