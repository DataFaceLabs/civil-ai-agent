"""Tests for run_agent structured output on the live path."""

import json
from unittest.mock import MagicMock, patch

import pytest

from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
from civilai_agent.runner import run_agent


@pytest.fixture(autouse=True)
def _legacy_agent_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CIVILAI_DRAFT_PIPELINE", raising=False)
    monkeypatch.delenv("CIVILAI_AGENT_HARDENING", raising=False)


def _context() -> WorkbenchContext:
    return WorkbenchContext(
        project_id="test",
        entity_id="ent-1",
        active_section_id="zoning",
        request="Draft zoning section.",
        workflow=AgentWorkflow.SECTION_DRAFT,
    )


def _structured_json() -> str:
    return json.dumps(
        {
            "suggested_language": "The parcel is zoned LI.",
            "caveats": [],
            "verification_steps": ["Confirm zoning with the city."],
            "data_gaps": [],
            "sources": [],
        }
    )


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_section_draft_run_materializes_draft_artifact(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    agent.model.config = {"model_id": "test-model"}
    mock_build.return_value = agent

    response = run_agent(_context())

    assert len(response.artifacts) == 1
    artifact = response.artifacts[0]
    assert artifact.type == "draft_section"
    assert artifact.section_id == "zoning"
    assert artifact.body == "The parcel is zoned LI."
    assert response.structured_draft is not None
    assert response.structured_draft["suggested_language"] == "The parcel is zoned LI."
    assert response.message == "The parcel is zoned LI."


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_assistant_chat_skips_structured_parsing(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = "Plain chat response."
    agent.model.config = {"model_id": "test-model"}
    mock_build.return_value = agent

    context = WorkbenchContext(
        project_id="test",
        request="What county is this parcel in?",
        workflow=AgentWorkflow.ASSISTANT_CHAT,
        chat_system_prompt="Chat system.",
    )
    response = run_agent(context)

    assert response.artifacts == ()
    assert response.structured_draft is None
    assert response.message == "Plain chat response."
    mock_build.assert_called_once_with(system_prompt="Chat system.")


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_non_section_draft_skips_structured_parsing(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    agent.model.config = {}
    mock_build.return_value = agent

    context = WorkbenchContext(
        project_id="test",
        entity_id="ent-1",
        request="What county is this parcel in?",
        workflow=AgentWorkflow.MINIMAL_QA,
    )
    response = run_agent(context)

    assert response.artifacts == ()
    assert response.structured_draft is None
    assert response.message == _structured_json()


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_section_draft_parse_failure_returns_warning_not_crash(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = "Plain prose without JSON."
    agent.model.config = {}
    mock_build.return_value = agent

    response = run_agent(_context())

    assert response.artifacts == ()
    assert response.structured_draft is None
    assert response.message == "Plain prose without JSON."
    assert any("could not be parsed" in w.lower() for w in response.guardrail_warnings)
