"""Assistant chat workflow — plain-text Q&A in the project conversation rail."""

from __future__ import annotations

from civilai_agent.models.context import WorkbenchContext

PLAIN_TEXT_GUARDS = (
    "Respond in clear plain text for the chat panel.",
    "Do not wrap the response in markdown code fences or JSON.",
    "Do not invent facts, permits, or utility commitments.",
    "Utility service area boundaries do not confirm capacity, pressure, or will-serve.",
    "Cite URLs only when returned by web_search_deduped in this run.",
)


def assistant_chat_prompt(context: WorkbenchContext) -> str:
    """Build the user prompt for assistant_chat workflow."""
    section = context.active_section_id or "the active section"
    parts: list[str] = []

    if context.chat_system_prompt.strip():
        parts.append(context.chat_system_prompt.strip())
    else:
        parts.append(
            f"You are the civil1.ai assistant helping an analyst with the {section} "
            "section of a feasibility study."
        )

    context_lines: list[str] = []
    if context.tenant_name:
        context_lines.append(f"Tenant: {context.tenant_name}")
    if context.project_name:
        context_lines.append(f"Project: {context.project_name}")
    if context.property_address:
        context_lines.append(f"Property: {context.property_address}")
    if context_lines:
        parts.append("Project context:\n" + "\n".join(context_lines))

    instructions = (
        list(context.chat_instructions) if context.chat_instructions else list(PLAIN_TEXT_GUARDS)
    )
    parts.append("Instructions:\n" + "\n".join(f"- {line}" for line in instructions))

    if context.thread_memory.strip():
        parts.append(context.thread_memory.strip())

    if context.field_context:
        field_lines = [
            f"  {key}: {value.strip()}"
            for key, value in sorted(context.field_context.items())
            if value.strip()
        ]
        if field_lines:
            parts.append("Known site facts:\n" + "\n".join(field_lines))

    if context.section_body_plain.strip():
        parts.append(
            "Current section draft (reference only):\n" + context.section_body_plain.strip()
        )

    parts.append(f"Analyst message:\n{context.request.strip()}")
    return "\n\n".join(parts)
