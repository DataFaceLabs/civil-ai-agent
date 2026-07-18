"""Tests for eval hardening entrypoint and gates."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from civilai_agent.hardening.run import run_hardened_section_draft
from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
from civilai_agent.pipeline.gates import missing_entity_gate


def test_missing_entity_gate_blocks() -> None:
    response = missing_entity_gate(None, "zoning")
    assert response is not None
    assert "not resolved" in response.message
    assert response.artifacts[0].status == "blocked"


def test_missing_entity_gate_passes_with_entity() -> None:
    assert missing_entity_gate("ent-1", "zoning") is None


@pytest.fixture
def section_draft_context() -> WorkbenchContext:
    return WorkbenchContext(
        project_id="eval",
        entity_id="ent-1",
        active_section_id="zoning",
        workflow=AgentWorkflow.SECTION_DRAFT,
        request="Draft zoning",
    )


def test_hardening_routes_utilities_to_pipeline(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    ctx = section_draft_context.model_copy(update={"active_section_id": "utilities"})
    mock_pipeline = MagicMock(return_value=MagicMock(message="utilities draft"))
    mock_fetch = MagicMock(
        return_value=MagicMock(
            entity_id="ent-1", section_id="utilities", facts={"facts": {"water_provider": "X"}}
        )
    )
    mock_gate = MagicMock(return_value=None)
    with (
        patch("civilai_agent.hardening.run.fetch_section_context", mock_fetch),
        patch("civilai_agent.hardening.run.zero_fact_gate", mock_gate),
        patch.dict(
            "civilai_agent.hardening.run._PIPELINE_RUNNERS",
            {"utilities": mock_pipeline},
        ),
    ):
        run_hardened_section_draft(ctx, dry_run=True)
    mock_pipeline.assert_called_once()


def test_hardening_routes_zoning_to_pipeline(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.setenv("CIVILAI_AGENT_HARDENING", "1")
    mock_pipeline = MagicMock(return_value=MagicMock(message="zoning draft"))
    mock_fetch = MagicMock(
        return_value=MagicMock(
            entity_id="ent-1", section_id="zoning", facts={"facts": {"zoning_code": "CS"}}
        )
    )
    mock_gate = MagicMock(return_value=None)
    with (
        patch("civilai_agent.hardening.run.fetch_section_context", mock_fetch),
        patch("civilai_agent.hardening.run.zero_fact_gate", mock_gate),
        patch.dict(
            "civilai_agent.hardening.run._PIPELINE_RUNNERS",
            {"zoning": mock_pipeline},
        ),
    ):
        run_hardened_section_draft(section_draft_context, dry_run=True)
    mock_pipeline.assert_called_once()


def test_hardening_toggle_in_runner(
    monkeypatch: pytest.MonkeyPatch, section_draft_context: WorkbenchContext
) -> None:
    monkeypatch.setenv("CIVILAI_AGENT_HARDENING", "1")
    monkeypatch.delenv("CIVILAI_DRAFT_PIPELINE", raising=False)
    with patch("civilai_agent.hardening.run.run_hardened_section_draft") as mock:
        mock.return_value = MagicMock(message="hardened")
        from civilai_agent.runner import run_agent

        run_agent(section_draft_context, dry_run=True)
    mock.assert_called_once()
