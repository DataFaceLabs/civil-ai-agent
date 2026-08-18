"""Explicit workflow orchestrators."""

from __future__ import annotations

from civilai_agent.models.context import WorkbenchContext
from civilai_agent.workflows.assistant_chat import assistant_chat_prompt

STRUCTURED_DRAFT_INSTRUCTION = """
Return your final section draft as a single JSON object (no markdown code fence) with this shape:
{
  "suggested_language": "ATX-Civil prose for the section",
  "caveats": ["optional caveat strings"],
  "verification_steps": ["SME verification steps for partial/unknown facts"],
  "data_gaps": ["explicit gaps not covered by known site facts"],
  "sources": [{"title": "...", "url": "https://...", "snippet": "..."}]
}
Only include "sources" entries for URLs returned by web_search_deduped in this run.
Populate verification_steps and data_gaps from known site facts with status partial or unknown.

suggested_language must use short paragraphs (1-3 sentences, blank lines between them),
paraphrase known site facts (do not paste multi-topic dumps), and never invent
"(See Exhibit: ...)" unless AVAILABLE_EXHIBITS lists that sheet. Scrub robotic stems such as
"rule extraction pending" into honest verification gaps. Never mention field data, available
data, governed fields, or project data in suggested_language. When a fact is unknown, write
that it is not currently known and should be confirmed.

If every site-fact tool call fails or returns no data for this entity, you MUST still
return the JSON object above -- never ask the user a question or request an address, parcel
ID, or other input; this is an unattended run and no reply is possible. Instead set
"suggested_language" to state plainly that the section facts are not currently known and
should be confirmed, and list what is missing in "data_gaps".

When known site facts already contain PROPERTY_ADDRESS, parcel identifiers, or other values,
draft from those values. Do not ask the analyst to re-provide information present in
known site facts or the Prompt Lab request.

When known site facts include markdown links such as [Nearest water main](https://...),
preserve those friendly labels with their HREFs in suggested_language (do not drop the URLs or
replace them with bare links).
""".strip()


def section_draft_prompt(context: WorkbenchContext) -> str:
    section = context.active_section_id or "the active section"
    entity = context.entity_id or "unknown entity"
    parts = [
        f"Draft feasibility language for section '{section}'.",
        f"Entity: {entity}",
        f"Proposed use: {context.proposed_use or 'not specified'}",
        f"Request: {context.request}",
        "This is an unattended section_draft run: never ask the user for an address, parcel ID,"
        " or other input. Return the required JSON object even when data is incomplete.",
        "Workflow: when entity_id is known, fetch site payload, section facts, determinations,"
        " and provenance first. When entity_id is unknown, draft only from Request and known site facts.",
    ]
    if context.field_context:
        parts.append("Known site facts:")
        for key, value in sorted(context.field_context.items()):
            if value.strip():
                parts.append(f"  {key}: {value}")
    parts.extend(["", STRUCTURED_DRAFT_INSTRUCTION])
    return "\n".join(parts)


def gap_analysis_prompt(context: WorkbenchContext) -> str:
    return (
        f"Identify data gaps for entity {context.entity_id or 'unknown'}.\n"
        f"Section focus: {context.active_section_id or 'all sections'}\n"
        f"Request: {context.request}\n"
        "Compare known site facts against what a complete feasibility study requires."
    )


def build_user_prompt(context: WorkbenchContext) -> str:
    if context.workflow and context.workflow.value == "assistant_chat":
        return assistant_chat_prompt(context)
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
        parts.append("Known site facts:")
        for key, value in sorted(context.field_context.items()):
            if value.strip():
                parts.append(f"  {key}: {value}")
    return "\n".join(parts)
