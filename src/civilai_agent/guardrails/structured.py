"""Structured output schema for section drafts."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from civilai_agent.guardrails.web_search_models import WebSearchResult


class SectionDraftOutput(BaseModel):
    """The structured JSON contract every section draft must satisfy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    suggested_language: str = Field(min_length=1)
    caveats: tuple[str, ...] = Field(default=())
    verification_steps: tuple[str, ...] = Field(default=())
    data_gaps: tuple[str, ...] = Field(default=())
    sources: tuple[WebSearchResult, ...] = Field(default=())


_FENCED_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _candidate_json_strings(text: str) -> list[str]:
    """Every plausible JSON substring in `text`, most-likely-correct first.

    The prompt asks for a bare JSON object with no fence, but models (Haiku 4.5
    observed live) sometimes prepend a conversational sentence and/or wrap the
    object in a ```json fence anyway. Rather than trust the model to follow the
    "no fence, no preamble" instruction exactly, extract defensively: a fenced
    block anywhere in the text, then the whole trimmed text, then the substring
    from the first '{' to the last '}' (catches an unfenced object with prose
    before or after it).
    """
    cleaned = text.strip()
    candidates: list[str] = []
    candidates.extend(m.group(1).strip() for m in _FENCED_BLOCK.finditer(cleaned))
    candidates.append(cleaned)
    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first != -1 and last > first:
        candidates.append(cleaned[first : last + 1])
    return candidates


def parse_structured_response(text: str) -> tuple[SectionDraftOutput | None, tuple[str, ...]]:
    errors: list[str] = []
    for candidate in _candidate_json_strings(text):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            errors.append(f"JSON parse error: {exc}")
            continue
        try:
            return SectionDraftOutput.model_validate(payload), ()
        except ValidationError as exc:
            errors.extend(str(err) for err in exc.errors())
            continue
    return None, tuple(errors)
