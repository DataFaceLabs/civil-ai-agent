"""Agent entrypoint — framework-agnostic run() for platform / AgentCore."""

from __future__ import annotations

import time
from typing import Any

from civilai_agent.agents.civil_analyst import build_civil_analyst_agent
from civilai_agent.config import settings
from civilai_agent.guardrails.finalize import finalize_text_output
from civilai_agent.guardrails.prefetch_search import derive_prefetch_queries
from civilai_agent.guardrails.shared import DEFAULT_GUARDRAILS
from civilai_agent.guardrails.web_search_models import WebSearchConfig
from civilai_agent.models.context import (
    AgentArtifact,
    AgentResponse,
    AgentWorkflow,
    Claim,
    TraceSummary,
    WorkbenchContext,
)
from civilai_agent.tools.web_search_tool import get_search_session, reset_search_session
from civilai_agent.workflows.section_draft import build_user_prompt


def _extract_message(result: Any) -> str:
    if isinstance(result, str):
        return result
    if hasattr(result, "message") and isinstance(result.message, str):
        return result.message
    return str(result)


def _agent_model_id(agent: Any) -> str | None:
    model = getattr(agent, "model", None)
    config = getattr(model, "config", None)
    if isinstance(config, dict):
        val = config.get("model_id")
        return val if isinstance(val, str) else None
    return None


def extract_token_usage(result: Any) -> tuple[int | None, int | None]:
    """Pull (input_tokens, output_tokens) from a Strands AgentResult, if present."""
    metrics = getattr(result, "metrics", None)
    usage = getattr(metrics, "accumulated_usage", None)
    if not isinstance(usage, dict):
        return None, None
    input_tokens = usage.get("inputTokens")
    output_tokens = usage.get("outputTokens")
    return (
        input_tokens if isinstance(input_tokens, int) else None,
        output_tokens if isinstance(output_tokens, int) else None,
    )


def _apply_search_policy(context: WorkbenchContext) -> WebSearchConfig:
    """Reset the search session from the platform-resolved policy envelope."""
    config = WebSearchConfig.from_search_run_policy(context.search_run_policy)
    reset_search_session(config)
    return config


def _run_prefetch_searches(context: WorkbenchContext, config: WebSearchConfig) -> None:
    """Execute deterministic prefetch queries before the agent tool loop."""
    if not config.is_active():
        return
    policy = context.search_run_policy
    queries = derive_prefetch_queries(
        context.field_context,
        search_context_hint=policy.search_context_hint,
        max_queries=policy.max_queries_per_run,
    )
    if not queries:
        return
    session = get_search_session()
    entity_id = context.entity_id or None
    restrict = bool(policy.allowed_domains)
    for query in queries:
        session.search(query, entity_id=entity_id, restrict_domains=restrict)


def run_legacy_agent(context: WorkbenchContext, *, dry_run: bool = False) -> AgentResponse:
    """Legacy Strands tool-loop path (no pipeline routing)."""
    search_config = _apply_search_policy(context)
    if not dry_run:
        _run_prefetch_searches(context, search_config)
    user_prompt = build_user_prompt(context)
    started = time.perf_counter()

    if dry_run:
        return AgentResponse(
            message=f"[dry-run] Would invoke agent with prompt:\n{user_prompt}",
            trace_summary=TraceSummary(tools_used=("dry_run",)),
        )

    system_prompt = (
        context.chat_system_prompt.strip()
        if context.workflow == AgentWorkflow.ASSISTANT_CHAT and context.chat_system_prompt.strip()
        else None
    )
    agent = build_civil_analyst_agent(system_prompt=system_prompt)
    raw = agent(user_prompt)
    message = _extract_message(raw)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    input_tokens, output_tokens = extract_token_usage(raw)

    session = get_search_session()
    use_structured = context.workflow == AgentWorkflow.SECTION_DRAFT
    web_search_trace = session.get_trace()
    display, structured, warnings = finalize_text_output(
        text=message,
        guardrails=DEFAULT_GUARDRAILS,
        web_search_trace=web_search_trace if web_search_trace else None,
        structured_mode=use_structured,
        section_id=context.active_section_id,
    )

    artifacts: list[AgentArtifact] = []
    if structured is not None:
        artifacts.append(
            AgentArtifact(
                type="draft_section",
                title=f"Draft — {context.active_section_id or 'section'}",
                status="partial",
                section_id=context.active_section_id,
                claims=(Claim(text=structured.suggested_language),),
                data_gaps=structured.data_gaps,
                body=structured.suggested_language,
                metadata={
                    "caveats": list(structured.caveats),
                    "verification_steps": list(structured.verification_steps),
                },
            )
        )

    trace = TraceSummary(
        tools_used=(
            "resolve_parcel",
            "get_section_facts",
            "get_site_payload",
            "run_determinations",
            "web_search_deduped",
        ),
        model_id=_agent_model_id(agent),
        latency_ms=elapsed_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        web_search_queries=session.executed_queries,
        dedupe_hits=session.dedupe_hits,
    )

    structured_dict = structured.model_dump() if structured is not None else None

    return AgentResponse(
        message=display,
        artifacts=tuple(artifacts),
        trace_summary=trace,
        structured_draft=structured_dict,
        guardrail_warnings=warnings,
    )


def run_agent(context: WorkbenchContext, *, dry_run: bool = False) -> AgentResponse:
    """Run the Civil Analyst agent and return a framework-agnostic response."""
    if settings().use_draft_pipeline and context.workflow == AgentWorkflow.SECTION_DRAFT:
        from civilai_agent.pipeline.run import run_section_draft

        return run_section_draft(context, dry_run=dry_run)

    return run_legacy_agent(context, dry_run=dry_run)
