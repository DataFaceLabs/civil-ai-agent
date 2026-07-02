"""Explicit workflow orchestrators."""

from __future__ import annotations

from civilai_agent.models.context import WorkbenchContext


def section_draft_prompt(context: WorkbenchContext) -> str:
    section = context.active_section_id or "the active section"
    entity = context.entity_id or "unknown entity"
    return (
        f"Draft feasibility language for section '{section}'.\n"
        f"Entity: {entity}\n"
        f"Proposed use: {context.proposed_use or 'not specified'}\n"
        f"Request: {context.request}\n"
        "Workflow: fetch site payload, section facts, determinations, and provenance first."
    )


def gap_analysis_prompt(context: WorkbenchContext) -> str:
    return (
        f"Identify data gaps for entity {context.entity_id or 'unknown'}.\n"
        f"Section focus: {context.active_section_id or 'all sections'}\n"
        f"Request: {context.request}\n"
        "Compare governed facts against what a complete feasibility study requires."
    )


def build_user_prompt(context: WorkbenchContext) -> str:
    if context.workflow and context.workflow.value == "section_draft":
        return section_draft_prompt(context)
    if context.workflow and context.workflow.value == "gap_analysis":
        return gap_analysis_prompt(context)
    parts = [context.request]
    if context.entity_id:
        parts.append(f"Entity ID: {context.entity_id}")
    if context.active_section_id:
        parts.append(f"Active section: {context.active_section_id}")
    if context.field_context:
        parts.append("Field context:")
        for key, value in sorted(context.field_context.items()):
            if value.strip():
                parts.append(f"  {key}: {value}")
    return "\n".join(parts)
