"""Explicit workflow orchestrators."""

from __future__ import annotations

from civilai_agent.models.context import WorkbenchContext

STRUCTURED_DRAFT_INSTRUCTION = """
Return your final section draft as a single JSON object (no markdown code fence) with this shape:
{
  "suggested_language": "ATX-Civil prose for the section",
  "caveats": ["optional caveat strings"],
  "verification_steps": ["SME verification steps for partial/unknown fields"],
  "data_gaps": ["explicit gaps not covered by governed data"],
  "sources": [{"title": "...", "url": "https://...", "snippet": "..."}]
}
Only include "sources" entries for URLs returned by web_search_deduped in this run.
Populate verification_steps and data_gaps from governed fields with status partial or unknown.

If every governed-data tool call fails or returns no data for this entity, you MUST still
return the JSON object above -- never ask the user a question or request an address, parcel
ID, or other input; this is an unattended run and no reply is possible. Instead set
"suggested_language" to state plainly that the section could not be drafted because no
governed data is available for this entity, and list what is missing in "data_gaps".
""".strip()


def section_draft_prompt(context: WorkbenchContext) -> str:
    section = context.active_section_id or "the active section"
    entity = context.entity_id or "unknown entity"
    parts = [
        f"Draft feasibility language for section '{section}'.",
        f"Entity: {entity}",
        f"Proposed use: {context.proposed_use or 'not specified'}",
        f"Request: {context.request}",
        "Workflow: fetch site payload, section facts, determinations, and provenance first.",
        "",
        STRUCTURED_DRAFT_INSTRUCTION,
    ]
    return "\n".join(parts)


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
