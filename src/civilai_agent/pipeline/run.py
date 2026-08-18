"""Pipeline entrypoint — swaps in behind run_agent() when CIVILAI_DRAFT_PIPELINE=1."""

from __future__ import annotations

import time

from civilai_agent.config import PIPELINE_DATA_API_TIMEOUT_DEFAULT, settings
from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.models.context import (
    AgentArtifact,
    AgentResponse,
    Claim,
    TraceSummary,
    WorkbenchContext,
)
from civilai_agent.pipeline.fetch import (
    SectionContext,
    false_ic_gap_warning,
    fetch_section_context,
    merge_impervious_hydrate,
)
from civilai_agent.pipeline.finalize import (
    append_fact_echo_warnings,
    finalize_pipeline_response,
)
from civilai_agent.pipeline.gates import zero_fact_gate
from civilai_agent.pipeline.specs import DraftSpec
from civilai_agent.tools.data_client import DataApiClient


def _data_client() -> DataApiClient:
    timeout = settings().data_api_timeout
    if timeout is None:
        timeout = PIPELINE_DATA_API_TIMEOUT_DEFAULT
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
    input_tokens: int | None = None,
    output_tokens: int | None = None,
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
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        structured_draft=structured.model_dump(),
        guardrail_warnings=guardrail_warnings,
    )


def _render_and_respond(
    spec: DraftSpec,
    *,
    section_id: str,
    format_directive: str,
    tenant_system_prompt: str,
) -> AgentResponse:
    """Single LLM render + response assembly, recording latency and token telemetry.

    Every LLM-rendered pipeline section funnels through here so token usage is captured
    uniformly (previously the pipeline reported zero tokens — see render.RenderResult).
    """
    from civilai_agent.pipeline.render import render_draft

    started = time.perf_counter()
    rendered = render_draft(
        spec, format_directive=format_directive, tenant_system_prompt=tenant_system_prompt
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return _response_from_structured(
        rendered.output,
        section_id=section_id,
        pipeline_path="render",
        trace_tools=("pipeline_fetch", "pipeline_dispatch", "pipeline_render"),
        branch_id=spec.branch_id,
        latency_ms=elapsed_ms,
        model_id=rendered.model_id,
        input_tokens=rendered.input_tokens,
        output_tokens=rendered.output_tokens,
    )


def _run_zoning_pipeline(
    ctx: SectionContext,
    *,
    dry_run: bool,
    format_directive: str = "",
    tenant_system_prompt: str = "",
) -> AgentResponse:
    from civilai_agent.pipeline.dispatch.zoning import dispatch_zoning
    from civilai_agent.pipeline.render import build_render_prompt
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
        prompt = build_render_prompt(spec, format_directive=format_directive)
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
        response = _render_and_respond(
            spec,
            section_id="zoning",
            format_directive=format_directive,
            tenant_system_prompt=tenant_system_prompt,
        )

    response = append_fact_echo_warnings(response, spec)
    warning = false_ic_gap_warning(response.message, ctx.hydrate_impervious_status)
    if warning:
        response = response.model_copy(
            update={"guardrail_warnings": (*response.guardrail_warnings, warning)}
        )
    return finalize_pipeline_response(response)


def _run_flood_pipeline(
    ctx: SectionContext,
    *,
    dry_run: bool,
    format_directive: str = "",
    tenant_system_prompt: str = "",
) -> AgentResponse:
    from civilai_agent.pipeline.dispatch.flood import dispatch_flood
    from civilai_agent.pipeline.render import build_render_prompt
    from civilai_agent.pipeline.templates.flood import render_flood_tier1

    spec = dispatch_flood(ctx)

    if spec.tier == 1:
        structured = render_flood_tier1(spec)
        response = _response_from_structured(
            structured,
            section_id="flood",
            pipeline_path="template",
            trace_tools=("pipeline_fetch", "pipeline_dispatch", "pipeline_template"),
            branch_id=spec.branch_id,
        )
    elif dry_run:
        prompt = build_render_prompt(spec, format_directive=format_directive)
        message = (
            f"[pipeline dry-run] would render flood branch={spec.branch_id} "
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
                    title="Draft — flood",
                    status="partial",
                    section_id="flood",
                    body=message,
                    metadata={
                        "pipeline_path": "render",
                        "branch_id": spec.branch_id,
                    },
                ),
            ),
        )
    else:
        response = _render_and_respond(
            spec,
            section_id="flood",
            format_directive=format_directive,
            tenant_system_prompt=tenant_system_prompt,
        )

    response = append_fact_echo_warnings(response, spec)
    return finalize_pipeline_response(response)


def _run_utilities_pipeline(
    ctx: SectionContext,
    *,
    dry_run: bool,
    format_directive: str = "",
    tenant_system_prompt: str = "",
) -> AgentResponse:
    from civilai_agent.pipeline.dispatch.utilities import dispatch_utilities
    from civilai_agent.pipeline.render import build_render_prompt

    spec = dispatch_utilities(ctx)

    if dry_run:
        prompt = build_render_prompt(spec, format_directive=format_directive)
        message = (
            f"[pipeline dry-run] would render utilities branch={spec.branch_id} "
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
                    title="Draft — utilities",
                    status="partial",
                    section_id="utilities",
                    body=message,
                    metadata={
                        "pipeline_path": "render",
                        "branch_id": spec.branch_id,
                    },
                ),
            ),
        )

    response = _render_and_respond(
        spec,
        section_id="utilities",
        format_directive=format_directive,
        tenant_system_prompt=tenant_system_prompt,
    )
    response = append_fact_echo_warnings(response, spec)
    return finalize_pipeline_response(response)


def _run_environmental_pipeline(
    ctx: SectionContext,
    *,
    dry_run: bool,
    format_directive: str = "",
    tenant_system_prompt: str = "",
) -> AgentResponse:
    from civilai_agent.pipeline.dispatch.environmental import dispatch_environmental
    from civilai_agent.pipeline.render import build_render_prompt
    from civilai_agent.pipeline.templates.environmental import render_environmental_tier1

    spec = dispatch_environmental(ctx)

    if spec.tier == 1:
        structured = render_environmental_tier1(spec)
        response = _response_from_structured(
            structured,
            section_id="environmental",
            pipeline_path="template",
            trace_tools=("pipeline_fetch", "pipeline_dispatch", "pipeline_template"),
            branch_id=spec.branch_id,
        )
    elif dry_run:
        prompt = build_render_prompt(spec, format_directive=format_directive)
        message = (
            f"[pipeline dry-run] would render environmental branch={spec.branch_id} "
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
                    title="Draft — environmental",
                    status="partial",
                    section_id="environmental",
                    body=message,
                    metadata={
                        "pipeline_path": "render",
                        "branch_id": spec.branch_id,
                    },
                ),
            ),
        )
    else:
        response = _render_and_respond(
            spec,
            section_id="environmental",
            format_directive=format_directive,
            tenant_system_prompt=tenant_system_prompt,
        )

    response = append_fact_echo_warnings(response, spec)
    return finalize_pipeline_response(response)


def _run_descriptive_pipeline(
    ctx: SectionContext,
    section_id: str,
    *,
    dry_run: bool,
    format_directive: str = "",
    tenant_system_prompt: str = "",
) -> AgentResponse:
    """Render-only path for descriptive sections (parcel, access) — no branch logic."""
    from civilai_agent.pipeline.dispatch.descriptive import dispatch_descriptive
    from civilai_agent.pipeline.render import build_render_prompt

    spec = dispatch_descriptive(ctx, section_id)

    if dry_run:
        prompt = build_render_prompt(spec, format_directive=format_directive)
        message = (
            f"[pipeline dry-run] would render {section_id} branch={spec.branch_id} "
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
                    title=f"Draft — {section_id}",
                    status="partial",
                    section_id=section_id,
                    body=message,
                    metadata={
                        "pipeline_path": "render",
                        "branch_id": spec.branch_id,
                    },
                ),
            ),
        )

    response = _render_and_respond(
        spec,
        section_id=section_id,
        format_directive=format_directive,
        tenant_system_prompt=tenant_system_prompt,
    )
    response = append_fact_echo_warnings(response, spec)
    return finalize_pipeline_response(response)


# Descriptive sections migrated off the legacy tool loop onto the single-render pipeline
# path. They present governed facts under the tenant template (no safety-gated verdict), so
# they share one render-only dispatcher instead of a bespoke per-section one.
_DESCRIPTIVE_SECTIONS = frozenset({"parcel", "access"})


def run_section_draft(context: WorkbenchContext, *, dry_run: bool = False) -> AgentResponse:
    """Deterministic fetch → gate → section dispatch or legacy fallback."""
    entity_id = context.entity_id
    section_id = context.active_section_id or "section"
    if not entity_id:
        return AgentResponse(
            message="[pipeline] No entity_id on context; cannot draft.",
            trace_summary=TraceSummary(tools_used=("pipeline_error",)),
        )

    client = _data_client()
    ctx = fetch_section_context(client, entity_id, section_id)
    from civilai_agent.pipeline.field_overrides import (
        apply_field_context_overrides,
        redact_unprompted_parcel_appraisal_facts,
        redact_unprompted_parcel_zoning_context,
    )

    ctx = apply_field_context_overrides(ctx, context.field_context)
    ctx = redact_unprompted_parcel_appraisal_facts(ctx, context.field_context)
    ctx = redact_unprompted_parcel_zoning_context(ctx, context.field_context)
    if section_id == "zoning":
        ctx = merge_impervious_hydrate(client, ctx, context.field_context)
    gated = zero_fact_gate(ctx)
    if gated is not None:
        return finalize_pipeline_response(gated)

    # context.request carries the tenant's configured Prompt Lab drafting template for this
    # section (subsection list) and context.system_prompt carries the tenant-wide format
    # mandate ("Format: h1 and h2 subsections with headings... Emit field data facts in
    # bold") -- this is what actually makes legacy-path sections (Parcel, Access) render
    # with real markdown structure. The pipeline's own dispatch/stems logic (Python-owned,
    # deterministic) remains the sole source of *content*; both are passed through only as
    # structural/style guides (see render.py), so pipeline-rendered sections come back with
    # the same heading structure as legacy-path sections instead of flat, unheaded prose.
    format_directive = context.request
    tenant_system_prompt = context.system_prompt

    if section_id == "zoning":
        return _run_zoning_pipeline(
            ctx,
            dry_run=dry_run,
            format_directive=format_directive,
            tenant_system_prompt=tenant_system_prompt,
        )

    if section_id == "flood":
        return _run_flood_pipeline(
            ctx,
            dry_run=dry_run,
            format_directive=format_directive,
            tenant_system_prompt=tenant_system_prompt,
        )

    if section_id == "utilities":
        return _run_utilities_pipeline(
            ctx,
            dry_run=dry_run,
            format_directive=format_directive,
            tenant_system_prompt=tenant_system_prompt,
        )

    if section_id == "environmental":
        return _run_environmental_pipeline(
            ctx,
            dry_run=dry_run,
            format_directive=format_directive,
            tenant_system_prompt=tenant_system_prompt,
        )

    if section_id in _DESCRIPTIVE_SECTIONS:
        return _run_descriptive_pipeline(
            ctx,
            section_id,
            dry_run=dry_run,
            format_directive=format_directive,
            tenant_system_prompt=tenant_system_prompt,
        )

    from civilai_agent.runner import run_legacy_agent

    response = run_legacy_agent(context, dry_run=dry_run)
    if response.artifacts:
        artifact = response.artifacts[0]
        new_meta = dict(artifact.metadata)
        new_meta["pipeline_path"] = "legacy"
        response = response.model_copy(
            update={"artifacts": (artifact.model_copy(update={"metadata": new_meta}),)}
        )
    return finalize_pipeline_response(response)
