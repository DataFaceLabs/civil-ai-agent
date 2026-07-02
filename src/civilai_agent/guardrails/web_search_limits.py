"""Per-invoke web search budget caps."""

from __future__ import annotations

from civilai_agent.guardrails.web_search_models import WebSearchConfig, WebSearchTraceEntry


def trace_within_budget(
    trace: tuple[WebSearchTraceEntry, ...],
    config: WebSearchConfig,
) -> bool:
    executed = sum(1 for entry in trace if not entry.dedupe_hit)
    return executed <= config.max_queries_per_invoke


def remaining_query_budget(
    trace: tuple[WebSearchTraceEntry, ...],
    config: WebSearchConfig,
) -> int:
    executed = sum(1 for entry in trace if not entry.dedupe_hit)
    return max(config.max_queries_per_invoke - executed, 0)
