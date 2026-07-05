"""Pipeline entrypoint — swaps in behind run_agent() when CIVILAI_DRAFT_PIPELINE=1."""

from __future__ import annotations

import os

from civilai_agent.models.context import AgentResponse, TraceSummary, WorkbenchContext
from civilai_agent.pipeline.fetch import fetch_section_context
from civilai_agent.pipeline.finalize import finalize_pipeline_response
from civilai_agent.pipeline.gates import zero_fact_gate
from civilai_agent.tools.data_client import DataApiClient


def _data_client() -> DataApiClient:
    timeout = float(os.getenv("CIVILAI_DATA_API_TIMEOUT", "180"))
    return DataApiClient(timeout=timeout)


def run_section_draft(context: WorkbenchContext, *, dry_run: bool = False) -> AgentResponse:
    """Deterministic fetch → gate → legacy fallback (until section dispatch lands)."""
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

    from civilai_agent.runner import run_legacy_agent

    response = run_legacy_agent(context, dry_run=dry_run)
    return finalize_pipeline_response(response)
