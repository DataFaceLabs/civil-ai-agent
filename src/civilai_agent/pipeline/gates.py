"""Pipeline gates: zero-fact short-circuit without LLM."""

from __future__ import annotations

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import (
    AgentArtifact,
    AgentResponse,
    Claim,
    TraceSummary,
)
from civilai_agent.pipeline.fetch import SectionContext, facts_nonempty

_SECTION_TITLES: dict[str, str] = {
    "zoning": "Zoning",
    "environmental": "Environmental (Edwards / CWQZ)",
    "flood": "Floodplain / FEMA",
    "utilities": "Utilities",
}


def _section_title(section_id: str) -> str:
    return _SECTION_TITLES.get(section_id, section_id.replace("-", " ").title())


def missing_entity_gate(entity_id: str | None, section_id: str) -> AgentResponse | None:
    """Block drafting when the workbench context has no resolved entity."""
    if entity_id:
        return None
    title = _section_title(section_id)
    suggested = (
        f"The {title} section could not be drafted because the parcel is not resolved "
        "(no entity_id). Resolve the address or parcel ID before requesting a section draft."
    )
    data_gaps = (
        "Parcel not resolved — entity_id is required for governed section facts.",
    )
    structured = SectionDraftOutput(
        suggested_language=suggested,
        caveats=(),
        verification_steps=(
            "Resolve the project parcel via address or parcel ID.",
            "Confirm the parcel exists in the ingested CAD snapshot for this county.",
        ),
        data_gaps=data_gaps,
        sources=(),
    )
    artifact = AgentArtifact(
        type="draft_section",
        title=f"Draft — {section_id}",
        status="blocked",
        section_id=section_id,
        claims=(Claim(text=suggested),),
        data_gaps=structured.data_gaps,
        body=suggested,
        metadata={
            "caveats": [],
            "verification_steps": list(structured.verification_steps),
            "pipeline_path": "gate_missing_entity",
        },
    )
    return AgentResponse(
        message=suggested,
        artifacts=(artifact,),
        trace_summary=TraceSummary(tools_used=("hardening_gate_missing_entity",)),
        structured_draft=structured.model_dump(),
        guardrail_warnings=(),
    )


def zero_fact_gate(ctx: SectionContext) -> AgentResponse | None:
    """Return a complete response when governed facts are absent; else None."""
    if facts_nonempty(ctx.facts):
        return None

    title = _section_title(ctx.section_id)
    error_summary = "; ".join(ctx.errors) if ctx.errors else "no governed fields returned"
    suggested = (
        f"The {title} section could not be drafted because no governed data is available "
        f"for entity {ctx.entity_id}. {error_summary}. Verify the entity resolves to a "
        "parcel in the ingested corpus before drafting this section."
    )
    data_gaps = [
        f"Governed {ctx.section_id} facts unavailable for entity {ctx.entity_id}",
        *([f"fetch error: {e}" for e in ctx.errors]),
    ]
    structured = SectionDraftOutput(
        suggested_language=suggested,
        caveats=(),
        verification_steps=(
            "Confirm entity_id resolves to an ingested parcel with section facts populated.",
            "Re-run after data API/runtime sources are available for this jurisdiction.",
        ),
        data_gaps=tuple(data_gaps),
        sources=(),
    )
    artifact = AgentArtifact(
        type="draft_section",
        title=f"Draft — {ctx.section_id}",
        status="partial",
        section_id=ctx.section_id,
        claims=(Claim(text=suggested),),
        data_gaps=structured.data_gaps,
        body=suggested,
        metadata={
            "caveats": list(structured.caveats),
            "verification_steps": list(structured.verification_steps),
            "pipeline_path": "gate_zero_facts",
        },
    )
    return AgentResponse(
        message=suggested,
        artifacts=(artifact,),
        trace_summary=TraceSummary(
            tools_used=("pipeline_fetch", "pipeline_gate_zero_facts"),
        ),
        structured_draft=structured.model_dump(),
        guardrail_warnings=(),
    )
