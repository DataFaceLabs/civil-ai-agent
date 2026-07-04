"""Tests for section draft workflow prompts."""

from civilai_agent.models.context import WorkbenchContext
from civilai_agent.workflows.section_draft import build_user_prompt, section_draft_prompt


def test_section_draft_prompt_requests_structured_json() -> None:
    context = WorkbenchContext(
        project_id="p",
        entity_id="ent-1",
        active_section_id="zoning",
        request="Draft it.",
    )
    prompt = section_draft_prompt(context)
    assert "suggested_language" in prompt
    assert "JSON object" in prompt


def test_build_user_prompt_uses_section_draft_for_workflow() -> None:
    from civilai_agent.models.context import AgentWorkflow

    context = WorkbenchContext(
        project_id="p",
        entity_id="ent-1",
        active_section_id="flood",
        request="Draft flood section.",
        workflow=AgentWorkflow.SECTION_DRAFT,
    )
    prompt = build_user_prompt(context)
    assert "flood" in prompt
    assert "suggested_language" in prompt
