"""Pipeline entrypoint — swaps in behind run_agent() when CIVILAI_DRAFT_PIPELINE=1."""

from __future__ import annotations

import os
import time

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import (
    AgentArtifact,
    AgentResponse,
    Claim,
    TraceSummary,
    WorkbenchContext,
)
from civilai_agent.pipeline.fetch import SectionContext, fetch_section_context
from civilai_agent.pipeline.finalize import (
    append_fact_echo_warnings,
    finalize_pipeline_response,
)
from civilai_agent.pipeline.gates import zero_fact_gate
from civilai_agent.tools.data_client import DataApiClient


def _data_client() -> DataApiClient:
    timeout = float(os.getenv("CIVILAI_DATA_API_TIMEOUT", "180"))
    return DataApiClient(timeout=timeout)


def _response_from_structured(
    structured: SectionDraftOutput,
    *,
    section_id: str,
    pipeline_path: str,
    trace_tools: tuple[str, ...],
    guardrail_warnings: tuple[str, ...] = (),
    branch_id: str | None = None,
    latency_ms: int | None = None,
    model_id: str | None = None,
) -> AgentResponse:
    metadata: dict[str, object] = {
        "caveats": list(structured.caveats),
        "verification_steps": list(structured.verification_steps),
        "pipeline_path": pipeline_path,
    }
    if branch_id:
        metadata["branch_id"] = branch_id
    artifact = AgentArtifact(
        type="draft_section",
        title=f"Draft — {section_id}",
        status="partial",
        section_id=section_id,
        claims=(Claim(text=structured.suggested_language),),
        data_gaps=structured.data_gaps,
        body=structured.suggested_language,
        metadata=metadata,
    )
    return AgentResponse(
        message=structured.suggested_language,
        artifacts=(artifact,),
        trace_summary=TraceSummary(
            tools_used=trace_tools,
            model_id=model_id,
            latency_ms=latency_ms,
        ),
        structured_draft=structured.model_dump(),
        guardrail_warnings=guardrail_warnings,
    )


def _run_zoning_pipeline(
    ctx: SectionContext,
    *,
    dry_run: bool,
) -> AgentResponse:
    from civilai_agent.pipeline.dispatch.zoning import dispatch_zoning
    from civilai_agent.pipeline.render import build_render_prompt, render_draft
    from civilai_agent.pipeline.templates.zoning import render_zoning_tier0

    spec = dispatch_zoning(ctx)

    if spec.tier == 0:
        structured = render_zoning_tier0(spec)
        response = _response_from_structured(
            structured,
            section_id="zoning",
            pipeline_path="template",
            trace_tools=("pipeline_fetch", "pipeline_dispatch", "pipeline_template"),
            branch_id=spec.branch_id,
        )
    elif dry_run:
        prompt = build_render_prompt(spec)
        message = (
            f"[pipeline dry-run] would render zoning branch={spec.branch_id} "
            f"tier={spec.tier}\n{prompt}"
        )
        return AgentResponse(
            message=message,
            trace_summary=TraceSummary(
                tools_used=(
                    "pipeline_fetch",
                    "pipeline_dispatch",
                    "pipeline_render_dry_run",
                ),
            ),
            artifacts=(
                AgentArtifact(
                    type="draft_section",
                    title="Draft — zoning",
                    status="partial",
                    section_id="zoning",
                    body=message,
                    metadata={
                        "pipeline_path": "render",
                        "branch_id": spec.branch_id,
                    },
                ),
            ),
        )
    else:
        started = time.perf_counter()
        structured = render_draft(spec)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response = _response_from_structured(
            structured,
            section_id="zoning",
            pipeline_path="render",
            trace_tools=("pipeline_fetch", "pipeline_dispatch", "pipeline_render"),
            branch_id=spec.branch_id,
            latency_ms=elapsed_ms,
        )

    response = append_fact_echo_warnings(response, spec)
    return finalize_pipeline_response(response)


def run_section_draft(context: WorkbenchContext, *, dry_run: bool = False) -> AgentResponse:
    """Deterministic fetch → gate → section dispatch (zoning) or legacy fallback."""
    entity_id = context.entity_id
    section_id = context.active_section_id or "section"
    if not entity_id:
        return AgentResponse(
            message="[pipeline] No entity_id on context; cannot draft.",
            trace_summary=TraceSummary(tools_used=("pipeline_error",)),
        )

    ctx = fetch_section_context(_data_client(), entity_id, section_id)
    gated = zero_fact_gate(ctx)
    if gated is not None:
        return finalize_pipeline_response(gated)

    if section_id == "zoning":
        return _run_zoning_pipeline(ctx, dry_run=dry_run)

    from civilai_agent.runner import run_legacy_agent

    response = run_legacy_agent(context, dry_run=dry_run)
    if response.artifacts:
        artifact = response.artifacts[0]
        new_meta = dict(artifact.metadata)
        new_meta["pipeline_path"] = "legacy"
        response = response.model_copy(
            update={
                "artifacts": (
                    artifact.model_copy(update={"metadata": new_meta}),
                )
            }
        )
    return finalize_pipeline_response(response)
