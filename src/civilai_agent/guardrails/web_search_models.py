"""Web search configuration and trace models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchDepth = Literal["basic", "advanced"]
WebSearchExecutionMode = Literal["server", "openai_native"]
WebSearchQueryMode = Literal["deterministic", "hybrid"]


class WebSearchConfig(BaseModel):
    """Session limits, domain policy, and provider knobs for web search."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    execution_mode: WebSearchExecutionMode = "server"
    query_mode: WebSearchQueryMode = "deterministic"
    restrict_provider_domains: bool = False
    max_queries_per_invoke: int = Field(default=3, ge=0, le=5)
    max_results_per_query: int = Field(default=5, ge=1, le=10)
    allowed_domains: tuple[str, ...] = ()
    blocked_domains: tuple[str, ...] = ()
    search_depth: SearchDepth = "basic"
    search_context_hint: str = ""
    include_trace_in_response: bool = True

    def is_active(self) -> bool:
        return self.enabled and self.max_queries_per_invoke > 0


class WebSearchResult(BaseModel):
    """A single provider hit (title, url, snippet)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    url: str
    snippet: str = ""


class WebSearchTraceEntry(BaseModel):
    """One executed (or deduped) query and its results, for the run trace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str
    results: tuple[WebSearchResult, ...] = ()
    dedupe_hit: bool = False
