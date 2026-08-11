"""Hardened section_draft — Python gates + dispatch/render for all default eval sections."""

from __future__ import annotations

from civilai_agent.models.context import (
    AgentArtifact,
    AgentResponse,
    WorkbenchContext,
)
from civilai_agent.pipeline.fetch import fetch_section_context
from civilai_agent.pipeline.finalize import finalize_pipeline_response
from civilai_agent.pipeline.gates import missing_entity_gate, zero_fact_gate
from civilai_agent.pipeline.run import (
    _data_client,
    _run_environmental_pipeline,
    _run_flood_pipeline,
    _run_utilities_pipeline,
    _run_zoning_pipeline,
)
from civilai_agent.runner import run_legacy_agent

_HARDENED_SECTIONS = frozenset({"zoning", "environmental", "flood", "utilities"})

_PIPELINE_RUNNERS = {
    "zoning": _run_zoning_pipeline,
    "environmental": _run_environmental_pipeline,
    "flood": _run_flood_pipeline,
    "utilities": _run_utilities_pipeline,
}


def run_hardened_section_draft(
    context: WorkbenchContext,
    *,
    dry_run: bool = False,
) -> AgentResponse:
    """Fetch → gate → dispatch/render for default sections; legacy for others."""
    section_id = context.active_section_id or "section"

    blocked = missing_entity_gate(context.entity_id, section_id)
    if blocked is not None:
        return blocked

    assert context.entity_id is not None
    ctx = fetch_section_context(_data_client(), context.entity_id, section_id)
    from civilai_agent.pipeline.field_overrides import apply_field_context_overrides

    ctx = apply_field_context_overrides(ctx, context.field_context)

    gated = zero_fact_gate(ctx)
    if gated is not None:
        return finalize_pipeline_response(gated)

    if section_id in _HARDENED_SECTIONS:
        runner = _PIPELINE_RUNNERS[section_id]
        return runner(ctx, dry_run=dry_run)

    response = run_legacy_agent(context, dry_run=dry_run)
    if response.artifacts:
        artifact = response.artifacts[0]
        meta = dict(artifact.metadata)
        meta["hardening_path"] = "legacy_fallback"
        response = response.model_copy(
            update={"artifacts": (artifact.model_copy(update={"metadata": meta}),)}
        )
    elif response.message:
        response = response.model_copy(
            update={
                "artifacts": (
                    AgentArtifact(
                        type="draft_section",
                        title=f"Draft — {section_id}",
                        status="partial",
                        section_id=section_id,
                        body=response.message,
                        metadata={"hardening_path": "legacy_fallback"},
                    ),
                )
            }
        )
    trace = response.trace_summary
    tools = (*trace.tools_used, "hardening_legacy_fallback")
    response = response.model_copy(
        update={"trace_summary": trace.model_copy(update={"tools_used": tools})}
    )
    return response
