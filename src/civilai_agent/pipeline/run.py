"""Pipeline entrypoint — swaps in behind run_agent() when CIVILAI_DRAFT_PIPELINE=1."""

from __future__ import annotations

from civilai_agent.models.context import AgentResponse, TraceSummary, WorkbenchContext


def run_section_draft(context: WorkbenchContext, *, dry_run: bool = False) -> AgentResponse:
    """Run the deterministic draft pipeline for one section (stub until Phase 1+)."""
    section = context.active_section_id or "section"
    if dry_run:
        message = f"[pipeline stub dry-run] section={section} entity={context.entity_id}"
    else:
        message = "[pipeline stub]"
    return AgentResponse(
        message=message,
        trace_summary=TraceSummary(tools_used=("pipeline_stub",)),
    )
