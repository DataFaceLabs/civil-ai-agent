"""Tests for CIVILAI_DRAFT_PIPELINE toggle in runner."""

from __future__ import annotations

import pytest

from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
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


def test_pipeline_toggle_uses_stub(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.setenv("CIVILAI_DRAFT_PIPELINE", "1")
    response = run_agent(section_draft_context, dry_run=True)
    assert "[pipeline stub" in response.message


def test_pipeline_toggle_off_uses_legacy_dry_run(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.delenv("CIVILAI_DRAFT_PIPELINE", raising=False)
    response = run_agent(section_draft_context, dry_run=True)
    assert "Would invoke agent with prompt" in response.message
    assert "[pipeline stub" not in response.message
