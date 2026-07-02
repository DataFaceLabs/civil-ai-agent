"""Deduped web search Strands tool."""

from __future__ import annotations

import json

from strands import tool

from civilai_agent.guardrails.web_search_models import WebSearchConfig
from civilai_agent.tools.web_search import SearchSession, domain_allowed

_session: SearchSession | None = None


def get_search_session() -> SearchSession:
    global _session
    if _session is None:
        _session = SearchSession(WebSearchConfig(enabled=True))
    return _session


def reset_search_session(config: WebSearchConfig | None = None) -> SearchSession:
    global _session
    _session = SearchSession(config or WebSearchConfig(enabled=True))
    return _session


@tool
def web_search_deduped(query: str, entity_id: str = "") -> str:
    """Search the public web for regulatory gaps not covered by governed data.

    Use only after resolve_parcel, get_section_facts, and run_determinations.
    Duplicate queries in the same session are rejected automatically.
    """
    session = get_search_session()
    if not session.config.is_active():
        return json.dumps({"results": [], "note": "web search disabled"})
    results = session.search(query, entity_id=entity_id or None)
    filtered = tuple(r for r in results if domain_allowed(r.url, session.config))
    return json.dumps(
        {
            "query": query,
            "results": [r.model_dump() for r in filtered],
            "dedupe_hit": len(results) == 0 and session.dedupe_hits > 0,
        }
    )
