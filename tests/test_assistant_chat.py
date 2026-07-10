"""Tests for assistant_chat workflow prompts."""

from civilai_agent.models.context import AgentWorkflow, WorkbenchContext
from civilai_agent.workflows.assistant_chat import assistant_chat_prompt


def test_assistant_chat_prompt_includes_context_and_plain_text_guards() -> None:
    context = WorkbenchContext(
        project_id="proj-1",
        request="What overlays apply here?",
        workflow=AgentWorkflow.ASSISTANT_CHAT,
        active_section_id="zoning",
        tenant_name="Demo Firm",
        project_name="Main Street Site",
        property_address="123 Main St",
        thread_memory="Recent turns:\n[Zoning] Analyst: prior question",
        section_body_plain="Draft paragraph about zoning.",
        field_context={"ZONING_REGS": "LI"},
        chat_system_prompt="Custom system prompt.",
        chat_instructions=("Use plain text only.",),
    )
    prompt = assistant_chat_prompt(context)
    assert "Custom system prompt." in prompt
    assert "Demo Firm" in prompt
    assert "Main Street Site" in prompt
    assert "123 Main St" in prompt
    assert "Recent turns:" in prompt
    assert "ZONING_REGS" in prompt
    assert "Draft paragraph" in prompt
    assert "What overlays apply here?" in prompt
    assert "Use plain text only." in prompt
