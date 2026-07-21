"""Single-call LLM renderer from DraftSpec (Phase 2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from strands import Agent

from civilai_agent.agents.civil_analyst import build_model
from civilai_agent.guardrails.finalize import finalize_text_output
from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.pipeline.specs import DraftSpec
from civilai_agent.workflows.section_draft import STRUCTURED_DRAFT_INSTRUCTION

RENDERER_SYSTEM_PROMPT = """
You are a civil feasibility prose renderer for land development projects in the Austin metroplex.

Rules:
- The branch has already been selected in Python. Render prose for that branch only; do not
  re-decide feasibility or contradict the injected governed facts, slots, or determinations.
- Include every required stem faithfully in suggested_language.
- List every missing_input under verification_steps and/or data_gaps with its resolution path.
- Utility service boundaries indicate coverage only - never claim capacity or will-serve.
- Do not invent facts when fields are empty; state uncertainty explicitly.
- Produce concise, ATX Civil-style feasibility language.
- Short paragraphs (1-3 sentences each) with blank lines between paragraphs in markdown.
  One topic per paragraph cluster; paraphrase governed field values - never paste multi-topic
  Compose dumps or robotic stems ("rule extraction pending", "Pending user input.").
- Do not invent "(See Exhibit: ...)" callouts. Cite an exhibit only when AVAILABLE_EXHIBITS
  (in governed field values or the formatting block) lists that sheet/map.
- No tools are available; all context is injected below. Leave sources empty.
- When Citations include ArcGIS Map Viewer URLs (apps/mapviewer), include each in
  suggested_language as a markdown link using the citation source_name as the label:
  [source_name](url). Do not omit these GIS viewer HREFs from the draft prose.
- If a "Section formatting requirements" block is provided, follow its structure (subsection
  headings, order) using markdown headings in suggested_language. Treat it as a formatting
  guide only - never source facts from it; governed facts, slots, and determinations above
  remain the only authoritative content.
""".strip()


def _message_from_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if hasattr(result, "message") and isinstance(result.message, str):
        return result.message
    return str(result)


def _compact(obj: Any) -> str:
    """Deterministic, minimal JSON for the render prompt.

    No indentation (~30-40% fewer tokens than indent=2) and sorted keys (stable ordering
    also helps prompt caching).
    """
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _render_field_values(facts: dict[str, Any]) -> dict[str, Any]:
    """Only the governed field values the renderer actually consumes.

    The full section-facts payload from the data API also carries an ``evidence`` block
    (raw per-field source arrays), plus ``provenance``, ``quality``, ``as_of``, and
    duplicate id metadata. The prose renderer never reads any of that -- the ``evidence``
    URLs are already distilled into ``spec.citations`` (see ``_build_citations`` in the
    dispatchers), so shipping the raw block re-sends the same sources a second time. On
    real UAT payloads this trims the render prompt ~60% with no change to the drafted
    prose. Note this only affects what the *prompt* sends; ``spec.facts`` still holds the
    full payload, so downstream fact-echo guardrails are unaffected.
    """
    if not isinstance(facts, dict):
        return {}
    inner = facts.get("facts")
    return inner if isinstance(inner, dict) else facts


def build_render_prompt(spec: DraftSpec, *, format_directive: str = "") -> str:
    """Compose the single user prompt for a renderer call."""
    missing = [item.model_dump() for item in spec.missing_inputs]
    stem_lines = "\n".join(f"- {stem}" for stem in spec.stems) or "- (none)"
    parts = [
        f"Render the {spec.section_id} section for entity {spec.entity_id}.",
        f"Branch (already selected - do not re-decide): {spec.branch_id}",
        f"Tier: {spec.tier}",
        "",
        "Template slots:",
        _compact(spec.slots),
        "",
        "Required prose stems:",
        stem_lines,
        "",
        "Governed field values (do not contradict):",
        _compact(_render_field_values(spec.facts)),
        "",
        "Determinations:",
        _compact(spec.determinations),
        "",
        "Citations (the only source list - cite from these):",
        _compact(spec.citations),
        "",
        "Missing inputs (surface each in verification_steps and/or data_gaps):",
        _compact(missing),
    ]
    if format_directive.strip():
        parts += [
            "",
            "Section formatting requirements (structure/style only - do not source facts "
            "from this; governed facts, slots, and determinations above are authoritative):",
            format_directive.strip(),
        ]
    parts += ["", STRUCTURED_DRAFT_INSTRUCTION]
    return "\n".join(parts)


def _renderer_system_prompt(tenant_system_prompt: str) -> str:
    if not tenant_system_prompt.strip():
        return RENDERER_SYSTEM_PROMPT
    return (
        f"{RENDERER_SYSTEM_PROMPT}\n\n"
        "Tenant drafting style requirements (style, tone, and format only - the rules above "
        "about governed facts, branches, and tools still control content; do not source facts "
        "from this block):\n"
        f"{tenant_system_prompt.strip()}"
    )


def build_renderer_agent(
    *,
    model_id: str | None = None,
    temperature: float = 0.2,
    tenant_system_prompt: str = "",
) -> Agent:
    """Strands agent with no tools - one constrained render call."""
    return Agent(
        model=build_model(temperature=temperature, model_id=model_id),
        system_prompt=_renderer_system_prompt(tenant_system_prompt),
        tools=[],
    )


@dataclass(frozen=True)
class RenderResult:
    """A render's structured output plus its token usage.

    Pipeline sections previously reported zero tokens because the renderer never
    surfaced usage the way the legacy tool-loop path does -- so per-draft cost on the
    pipeline was invisible. Carrying it here lets the pipeline record real telemetry.
    """

    output: SectionDraftOutput
    input_tokens: int | None = None
    output_tokens: int | None = None
    model_id: str | None = None


def _token_usage(raw: Any) -> tuple[int | None, int | None]:
    """Best-effort (input, output) token counts from a Strands AgentResult."""
    usage = getattr(getattr(raw, "metrics", None), "accumulated_usage", None)
    if not isinstance(usage, dict):
        return None, None
    input_tokens = usage.get("inputTokens")
    output_tokens = usage.get("outputTokens")
    return (
        input_tokens if isinstance(input_tokens, int) else None,
        output_tokens if isinstance(output_tokens, int) else None,
    )


def _agent_model_id(agent: Agent) -> str | None:
    config = getattr(getattr(agent, "model", None), "config", None)
    if isinstance(config, dict):
        value = config.get("model_id")
        return value if isinstance(value, str) else None
    return None


def render_draft(
    spec: DraftSpec,
    *,
    format_directive: str = "",
    tenant_system_prompt: str = "",
    model_id: str | None = None,
) -> RenderResult:
    """Render the spec with one LLM call; retry once on structured-parse failure.

    The retry re-sends the same prompt with the parse error appended so the model
    can correct its JSON. A second failure raises - never loop unbounded. Token usage
    is summed across attempts so a retry's cost is not lost.
    """
    agent = build_renderer_agent(model_id=model_id, tenant_system_prompt=tenant_system_prompt)
    prompt = build_render_prompt(spec, format_directive=format_directive)
    detail = ""
    input_total = 0
    output_total = 0
    for attempt in range(2):
        raw = agent(prompt)
        in_tokens, out_tokens = _token_usage(raw)
        input_total += in_tokens or 0
        output_total += out_tokens or 0
        text = _message_from_result(raw)
        _, structured, warnings = finalize_text_output(
            text=text,
            structured_mode=True,
            section_id=spec.section_id,
        )
        if structured is not None:
            return RenderResult(
                output=structured,
                input_tokens=input_total or None,
                output_tokens=output_total or None,
                model_id=_agent_model_id(agent),
            )
        detail = "; ".join(warnings) or "structured response could not be parsed"
        if attempt == 0:
            prompt = (
                f"{prompt}\n\nYour previous response failed structured validation "
                f"({detail}). Respond again with ONLY the JSON object, no prose."
            )
    raise RuntimeError(f"Renderer failed to produce structured output: {detail}")
