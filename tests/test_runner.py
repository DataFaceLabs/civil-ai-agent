"""Tests for run_agent structured output on the live path."""

import json
from unittest.mock import MagicMock, patch

import pytest

from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
from civilai_agent.runner import run_agent
from civilai_agent.tools.zoning_rails import get_zoning_scenario, set_zoning_scenario


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
    mock_build.assert_called_once_with(
        system_prompt="Chat system.",
        model_id=None,
        temperature=0.2,
    )


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_section_draft_consumes_platform_resolved_prompt_config(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    agent.model.config = {"model_id": "configured-model"}
    mock_build.return_value = agent

    context = _context().model_copy(
        update={
            "system_prompt": "Tenant section system prompt.",
            "model_id": "configured-model",
            "temperature": 0.1,
            "guardrails": {
                "forbiddenPhrases": ["guaranteed approval"],
                "requiredDisclaimers": [],
                "enforceGuardrails": False,
            },
        }
    )
    run_agent(context)

    mock_build.assert_called_once_with(
        system_prompt="Tenant section system prompt.",
        model_id="configured-model",
        temperature=0.1,
    )


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


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_section_draft_blocks_when_entity_and_fields_missing(mock_build: MagicMock) -> None:
    context = WorkbenchContext(
        project_id="test",
        entity_id=None,
        active_section_id="parcel",
        request="Draft parcel section.",
        workflow=AgentWorkflow.SECTION_DRAFT,
        field_context={},
    )
    response = run_agent(context)
    mock_build.assert_not_called()
    assert response.artifacts
    assert (
        response.artifacts[0].metadata.get("blocked_reason") == "missing_entity_and_field_context"
    )
    assert "parcel is not resolved" in response.message.lower()
    assert any("missing entity_id" in w.lower() for w in response.guardrail_warnings)


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_section_draft_runs_when_fields_present_without_entity(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    agent.model.config = {}
    mock_build.return_value = agent

    context = WorkbenchContext(
        project_id="test",
        entity_id=None,
        active_section_id="parcel",
        request="Draft parcel section.",
        workflow=AgentWorkflow.SECTION_DRAFT,
        field_context={"PROPERTY_ADDRESS": "123 Main St, Austin, TX"},
    )
    response = run_agent(context)
    mock_build.assert_called_once()
    assert response.structured_draft is not None


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_parcel_draft_does_not_install_zoning_rails(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    agent.model.config = {}
    mock_build.return_value = agent
    set_zoning_scenario({"analysis_basis": "proposed"})

    context = WorkbenchContext(
        project_id="test",
        entity_id="ent-1",
        active_section_id="parcel",
        request="Draft parcel section.",
        workflow=AgentWorkflow.SECTION_DRAFT,
        field_context={
            "PROPERTY_ADDRESS": "RR 2338, Georgetown, TX",
            "GOVERNING_JURIS": "Georgetown",
            "MIN_LOT_SIZE": "12,000 sq ft",
            "SETBACKS": "Front: 20 ft; Side: 10 ft; Rear: 10 ft",
            "IMPERVIOUS_COVER_LIMIT": "50%",
            "ZONING_REGS": "MF-1 — Sec. 6.02.080",
            "ZONING_ANALYSIS_BASIS": "proposed",
            "ZONING_SCENARIO_LABEL": "Rezone to MF-1",
        },
        zoning_scenario={
            "analysis_basis": "proposed",
            "active_scenario_id": "sc-1",
            "scenarios": [
                {
                    "scenario_id": "sc-1",
                    "status": "accepted",
                    "label": "MF-1",
                    "proposed": {
                        "fields": {
                            "MIN_LOT_SIZE": {"value": "12,000 sq ft"},
                            "ZONING_REGS": {"value": "MF-1"},
                        }
                    },
                }
            ],
        },
    )
    response = run_agent(context)
    mock_build.assert_called_once()
    assert response.structured_draft is not None
    assert get_zoning_scenario() is None
    # Prompt Lab parcel allowlist must not gain DSI codes from the proposed rail.
    # (run_legacy_agent dumps field_context into the user prompt.)
    user_prompt = agent.call_args.args[0]
    assert "12,000 sq ft" not in user_prompt
    assert "MIN_LOT_SIZE" not in user_prompt
    assert "IMPERVIOUS_COVER_LIMIT" not in user_prompt
    assert "ZONING_REGS" not in user_prompt
    assert "ZONING_ANALYSIS_BASIS" not in user_prompt
    assert "Rezone to MF-1" not in user_prompt
    assert "RR 2338, Georgetown, TX" in user_prompt
    set_zoning_scenario(None)


@patch("civilai_agent.runner.build_civil_analyst_agent")
def test_zoning_draft_installs_zoning_rails(mock_build: MagicMock) -> None:
    agent = MagicMock()
    agent.return_value = _structured_json()
    agent.model.config = {}
    mock_build.return_value = agent
    scenario = {
        "analysis_basis": "proposed",
        "active_scenario_id": "sc-1",
        "scenarios": [
            {
                "scenario_id": "sc-1",
                "status": "accepted",
                "label": "MF-1",
                "proposed": {"fields": {"ZONING_REGS": {"value": "MF-1"}}},
            }
        ],
    }
    context = WorkbenchContext(
        project_id="test",
        entity_id="ent-1",
        active_section_id="zoning",
        request="Draft zoning section.",
        workflow=AgentWorkflow.SECTION_DRAFT,
        field_context={"ZONING_REGS": "SF-2"},
        zoning_scenario=scenario,
    )
    run_agent(context)
    installed = get_zoning_scenario()
    assert installed is not None
    assert installed["active_scenario_id"] == "sc-1"
    set_zoning_scenario(None)
