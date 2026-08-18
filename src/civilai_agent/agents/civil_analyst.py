"""Civil Analyst Strands agent definition."""

from __future__ import annotations

from strands import Agent
from strands.models.model import Model

from civilai_agent.bedrock import build_bedrock_model
from civilai_agent.config import settings
from civilai_agent.tools.facts import (
    get_provenance,
    get_section_facts,
    resolve_parcel,
    run_determinations,
)
from civilai_agent.tools.web_search_tool import web_search_deduped
from civilai_agent.tools.zoning_rails import get_zoning_comparisons, get_zoning_rails

# NOTE: get_site_payload is deliberately NOT in this agent's toolset. It returns the full
# multi-section FE SitePayload (~30k tokens for a real entity), and the Strands tool loop
# resends every tool result on each subsequent turn -- so one get_site_payload call was
# compounding to tens of thousands of input tokens per draft (the dominant driver of the
# 2026-07 cost spike). A single-section draft only needs that section's governed facts
# (get_section_facts) plus determinations; cross-section context is not required. The tool
# function still exists in tools.facts for any caller that genuinely needs it.
CIVIL_ANALYST_SYSTEM_PROMPT = """
You are a civil feasibility analyst for land development projects in the Austin metroplex.

Rules:
- When entity_id is available, use get_section_facts for the active section and
  run_determinations before drafting conclusions. Call resolve_parcel only when entity_id
  is not already provided. Fetch only the data the active section needs.
- When drafting the zoning section and a Zoning Change scenario is active, call
  get_zoning_rails and get_zoning_comparisons before drafting zoning conclusions. Do not
  call those tools for other sections. Cite only ordinance evidence those tools return —
  never invent section numbers or dimensional standards (lot size, setbacks, coverage,
  height, IC) from memory; DSI-backed values must come from the tool payload. If
  analysis_basis is proposed, treat proposed-rail values as the study basis and label the
  draft as analyzed under proposed zoning.
- Never perform the same external web search twice; web_search_deduped rejects duplicates.
- Utility service boundaries indicate coverage only — never claim capacity or will-serve.
- Do not invent facts when values are empty or unknown; write that the fact is not
  currently known and should be confirmed. Never mention field data, available data,
  governed fields, or project data in drafted prose.
- Cite known sources; use web search only for gaps not in the lake.
- Produce concise, ATX Civil-style feasibility language when asked to draft.
""".strip()


def build_model(*, temperature: float = 0.2, model_id: str | None = None) -> Model:
    """Build the configured provider's Strands model (Bedrock default)."""
    provider = settings().model_provider.strip().lower()
    if provider == "openai":
        from civilai_agent.openai_model import build_openai_model

        return build_openai_model(temperature=temperature, model_id=model_id)
    return build_bedrock_model(temperature=temperature, model_id=model_id)


def build_civil_analyst_agent(
    *,
    temperature: float = 0.2,
    system_prompt: str | None = None,
    model_id: str | None = None,
) -> Agent:
    prompt = (
        system_prompt.strip()
        if system_prompt and system_prompt.strip()
        else CIVIL_ANALYST_SYSTEM_PROMPT
    )
    return Agent(
        model=build_model(temperature=temperature, model_id=model_id),
        system_prompt=prompt,
        tools=[
            resolve_parcel,
            get_section_facts,
            run_determinations,
            get_provenance,
            get_zoning_rails,
            get_zoning_comparisons,
            web_search_deduped,
        ],
    )
