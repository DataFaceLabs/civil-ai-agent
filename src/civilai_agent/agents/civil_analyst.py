"""Civil Analyst Strands agent definition."""

from __future__ import annotations

from strands import Agent

from civilai_agent.bedrock import build_bedrock_model
from civilai_agent.tools.facts import (
    get_provenance,
    get_section_facts,
    get_site_payload,
    resolve_parcel,
    run_determinations,
)
from civilai_agent.tools.web_search_tool import web_search_deduped

CIVIL_ANALYST_SYSTEM_PROMPT = """
You are a civil feasibility analyst for land development projects in the Austin metroplex.

Rules:
- Always use resolve_parcel, get_section_facts, get_site_payload, and run_determinations
  before drafting conclusions when entity_id or parcel context is available.
- Never perform the same external web search twice; web_search_deduped rejects duplicates.
- Utility service boundaries indicate coverage only — never claim capacity or will-serve.
- Do not invent facts when fields are empty or unavailable; state uncertainty explicitly.
- Cite governed data sources; use web search only for gaps not in the lake.
- Produce concise, ATX Civil-style feasibility language when asked to draft.
""".strip()


def build_civil_analyst_agent(*, temperature: float = 0.2) -> Agent:
    return Agent(
        model=build_bedrock_model(temperature=temperature),
        system_prompt=CIVIL_ANALYST_SYSTEM_PROMPT,
        tools=[
            resolve_parcel,
            get_section_facts,
            get_site_payload,
            run_determinations,
            get_provenance,
            web_search_deduped,
        ],
    )
