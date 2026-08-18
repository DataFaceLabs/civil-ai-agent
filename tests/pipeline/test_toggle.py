"""Tests for CIVILAI_DRAFT_PIPELINE toggle in runner."""

from __future__ import annotations

import pytest

from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.runner import run_agent


@pytest.fixture
def section_draft_context() -> WorkbenchContext:
    return WorkbenchContext(
        project_id="test",
        entity_id="ent-abc",
        active_section_id="zoning",
        workflow=AgentWorkflow.SECTION_DRAFT,
        request="Draft the Zoning section.",
    )


def test_pipeline_toggle_zoning_uses_render_dry_run_when_facts_present(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.setenv("CIVILAI_DRAFT_PIPELINE", "1")

    def fake_fetch(_client, entity_id: str, section_id: str) -> SectionContext:
        return SectionContext(
            entity_id=entity_id,
            section_id=section_id,
            facts={"facts": {"zoning_code": "CS", "allowed_use_flags": "[]"}},
            determinations={
                "determinations": [
                    {
                        "determination_id": "zoning_district",
                        "inputs_used": {
                            "jurisdiction.jurisdiction_primary": "City of Austin",
                            "jurisdiction.in_city_limits": True,
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr("civilai_agent.pipeline.run.fetch_section_context", fake_fetch)
    response = run_agent(section_draft_context, dry_run=True)
    assert "[pipeline dry-run] would render zoning" in response.message
    assert "Would invoke agent" not in response.message


def test_pipeline_toggle_zero_fact_gate_without_llm(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.setenv("CIVILAI_DRAFT_PIPELINE", "1")

    def fake_fetch(_client, entity_id: str, section_id: str) -> SectionContext:
        return SectionContext(
            entity_id=entity_id,
            section_id=section_id,
            facts=None,
            errors=["get_section_facts: 503"],
        )

    monkeypatch.setattr("civilai_agent.pipeline.run.fetch_section_context", fake_fetch)
    response = run_agent(section_draft_context, dry_run=True)
    assert "not currently known" in response.message
    assert "Would invoke agent" not in response.message


def test_pipeline_toggle_off_uses_legacy_dry_run(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.delenv("CIVILAI_DRAFT_PIPELINE", raising=False)
    monkeypatch.delenv("CIVILAI_AGENT_HARDENING", raising=False)
    response = run_agent(section_draft_context, dry_run=True)
    assert "Would invoke agent with prompt" in response.message
