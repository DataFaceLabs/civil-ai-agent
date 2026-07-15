"""Post-process agent outputs (guardrails + structured parsing)."""

from __future__ import annotations

from civilai_agent.guardrails.shared import (
    DEFAULT_GUARDRAILS,
    GuardrailConfig,
    evaluate_guardrails,
    evaluate_structured_guardrails,
)
from civilai_agent.guardrails.structured import SectionDraftOutput, parse_structured_response
from civilai_agent.guardrails.web_search_models import WebSearchTraceEntry


def _filter_structured_sources(
    structured: SectionDraftOutput,
    web_search_trace: tuple[WebSearchTraceEntry, ...],
) -> SectionDraftOutput:
    if not web_search_trace:
        return structured.model_copy(update={"sources": ()})
    allowed_urls = {hit.url for entry in web_search_trace for hit in entry.results if hit.url}
    if not allowed_urls:
        return structured.model_copy(update={"sources": ()})
    filtered = tuple(source for source in structured.sources if source.url in allowed_urls)
    return structured.model_copy(update={"sources": filtered})


def finalize_text_output(
    *,
    text: str,
    guardrails: GuardrailConfig | None = None,
    web_search_trace: tuple[WebSearchTraceEntry, ...] | None = None,
    structured_mode: bool = False,
    section_id: str | None = None,
) -> tuple[str, SectionDraftOutput | None, tuple[str, ...]]:
    cfg = guardrails or DEFAULT_GUARDRAILS
    structured: SectionDraftOutput | None = None
    warnings: tuple[str, ...]
    if structured_mode:
        structured, parse_errors = parse_structured_response(text)
        if structured is None:
            # Parse/format failures are soft: enforceGuardrails covers content policy
            # (forbidden phrases / required disclaimers), not JSON schema. Hard-failing
            # here made Prompt Lab enforce=true turn intermittents and prose-shaped
            # Lab prompts into UI-blocking errors (UAT 2026-07-14).
            detail = "; ".join(parse_errors) or "Structured response could not be parsed."
            warnings = (f"Structured response could not be parsed: {detail}",)
            return text, None, warnings
        if web_search_trace:
            structured = _filter_structured_sources(structured, web_search_trace)
        warnings = evaluate_structured_guardrails(structured, cfg, section_id=section_id)
        display = structured.suggested_language
    else:
        warnings = evaluate_guardrails(text, cfg, section_id=section_id)
        display = text

    if cfg.enforce and warnings:
        raise RuntimeError(f"Agent guardrails violated: {'; '.join(warnings)}")

    return display, structured, warnings
