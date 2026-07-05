"""Single-call LLM renderer from DraftSpec (Phase 2)."""

from __future__ import annotations

import json
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
- Utility service boundaries indicate coverage only — never claim capacity or will-serve.
- Do not invent facts when fields are empty; state uncertainty explicitly.
- Produce concise, ATX Civil-style feasibility language.
- No tools are available; all context is injected below. Leave sources empty.
""".strip()


def _message_from_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if hasattr(result, "message") and isinstance(result.message, str):
        return result.message
    return str(result)


def build_render_prompt(spec: DraftSpec) -> str:
    """Compose the single user prompt for a renderer call."""
    missing = [item.model_dump() for item in spec.missing_inputs]
    stem_lines = "\n".join(f"- {stem}" for stem in spec.stems) or "- (none)"
    parts = [
        f"Render the {spec.section_id} section for entity {spec.entity_id}.",
        f"Branch (already selected — do not re-decide): {spec.branch_id}",
        f"Tier: {spec.tier}",
        "",
        "Template slots:",
        json.dumps(spec.slots, indent=2, sort_keys=True),
        "",
        "Required prose stems:",
        stem_lines,
        "",
        "Governed facts (do not contradict):",
        json.dumps(spec.facts, indent=2, sort_keys=True),
        "",
        "Determinations:",
        json.dumps(spec.determinations, indent=2, sort_keys=True),
        "",
        "Citations:",
        json.dumps(spec.citations, indent=2, sort_keys=True),
        "",
        "Missing inputs (surface each in verification_steps and/or data_gaps):",
        json.dumps(missing, indent=2, sort_keys=True),
        "",
        STRUCTURED_DRAFT_INSTRUCTION,
    ]
    return "\n".join(parts)


def build_renderer_agent(*, model_id: str | None = None, temperature: float = 0.2) -> Agent:
    """Strands agent with no tools — one constrained render call."""
    return Agent(
        model=build_model(temperature=temperature, model_id=model_id),
        system_prompt=RENDERER_SYSTEM_PROMPT,
        tools=[],
    )


def render_draft(spec: DraftSpec, *, model_id: str | None = None) -> SectionDraftOutput:
    """Render the spec with one LLM call; retry once on structured-parse failure.

    The retry re-sends the same prompt with the parse error appended so the model
    can correct its JSON. A second failure raises — never loop unbounded.
    """
    agent = build_renderer_agent(model_id=model_id)
    prompt = build_render_prompt(spec)
    detail = ""
    for attempt in range(2):
        raw = agent(prompt)
        text = _message_from_result(raw)
        _, structured, warnings = finalize_text_output(
            text=text,
            structured_mode=True,
            section_id=spec.section_id,
        )
        if structured is not None:
            return structured
        detail = "; ".join(warnings) or "structured response could not be parsed"
        if attempt == 0:
            prompt = (
                f"{prompt}\n\nYour previous response failed structured validation "
                f"({detail}). Respond again with ONLY the JSON object, no prose."
            )
    raise RuntimeError(f"Renderer failed to produce structured output: {detail}")
