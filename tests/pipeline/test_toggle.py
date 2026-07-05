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


def test_pipeline_toggle_falls_back_to_legacy_dry_run_when_facts_present(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.setenv("CIVILAI_DRAFT_PIPELINE", "1")

    def fake_fetch(_client, entity_id: str, section_id: str) -> SectionContext:
        return SectionContext(
            entity_id=entity_id,
            section_id=section_id,
            facts={"facts": {"zoning_code": "CS"}},
        )

    monkeypatch.setattr("civilai_agent.pipeline.run.fetch_section_context", fake_fetch)
    response = run_agent(section_draft_context, dry_run=True)
    assert "Would invoke agent with prompt" in response.message


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
    assert "could not be drafted" in response.message
    assert "Would invoke agent" not in response.message


def test_pipeline_toggle_off_uses_legacy_dry_run(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.delenv("CIVILAI_DRAFT_PIPELINE", raising=False)
    response = run_agent(section_draft_context, dry_run=True)
    assert "Would invoke agent with prompt" in response.message
