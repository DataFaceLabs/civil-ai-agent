"""Structured output schema for section drafts."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from civilai_agent.guardrails.web_search_models import WebSearchResult


class SectionDraftOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    suggested_language: str = Field(min_length=1)
    caveats: tuple[str, ...] = Field(default=())
    verification_steps: tuple[str, ...] = Field(default=())
    data_gaps: tuple[str, ...] = Field(default=())
    sources: tuple[WebSearchResult, ...] = Field(default=())


def parse_structured_response(text: str) -> tuple[SectionDraftOutput | None, tuple[str, ...]]:
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)```\s*$", cleaned, re.DOTALL | re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, (f"JSON parse error: {exc}",)
    try:
        return SectionDraftOutput.model_validate(payload), ()
    except ValidationError as exc:
        return None, tuple(str(err) for err in exc.errors())
