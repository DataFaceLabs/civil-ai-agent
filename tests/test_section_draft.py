"""Tests for section draft workflow prompts."""

from civilai_agent.models.context import WorkbenchContext
from civilai_agent.workflows.section_draft import build_user_prompt, section_draft_prompt


def test_section_draft_prompt_preserves_gis_markdown_hrefs() -> None:
    prompt = section_draft_prompt(
        WorkbenchContext(
            project_id="p",
            entity_id="ent-1",
            active_section_id="utilities",
            request="Draft it.",
        )
    )
    assert "markdown links" in prompt.lower()
    assert "Nearest water main" in prompt
    assert "friendly labels" in prompt
    assert "HREFs" in prompt or "href" in prompt.lower()


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


def test_section_draft_prompt_forbids_interactive_questions() -> None:
    from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
    from civilai_agent.workflows.section_draft import section_draft_prompt

    prompt = section_draft_prompt(
        WorkbenchContext(
            project_id="test",
            entity_id=None,
            active_section_id="parcel",
            request="Draft parcel using Prompt Lab template.",
            workflow=AgentWorkflow.SECTION_DRAFT,
            field_context={"PROPERTY_ADDRESS": "123 Main St, Austin, TX"},
        )
    )
    assert "never ask the user" in prompt.lower()
    assert "PROPERTY_ADDRESS: 123 Main St, Austin, TX" in prompt
    assert "Known site facts:" in prompt
    assert "Field context:" not in prompt
    assert "unknown entity" in prompt


def test_section_draft_prompt_includes_structured_contract() -> None:
    from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
    from civilai_agent.workflows.section_draft import section_draft_prompt

    prompt = section_draft_prompt(
        WorkbenchContext(
            project_id="test",
            entity_id="ent-1",
            active_section_id="zoning",
            request="Draft zoning.",
            workflow=AgentWorkflow.SECTION_DRAFT,
        )
    )
    assert '"suggested_language"' in prompt
    assert "not currently known and should be confirmed" in prompt
    assert "no governed data is available" not in prompt
