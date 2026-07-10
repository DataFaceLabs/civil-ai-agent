"""Search run policy — platform-resolved envelope for governed web search."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WebSearchQueryMode = Literal["deterministic", "hybrid"]


class SearchRunPolicy(BaseModel):
    """Resolved search policy passed from platform orchestration into the agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    search_context_hint: str = ""
    allowed_domains: tuple[str, ...] = ()
    blocked_domains: tuple[str, ...] = ()
    max_queries_per_run: int = Field(default=3, ge=0, le=5)
    query_mode: WebSearchQueryMode = "deterministic"
