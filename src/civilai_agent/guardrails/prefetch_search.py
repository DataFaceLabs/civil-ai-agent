"""Derive prefetch web search queries from field context."""

from __future__ import annotations

import re

from civilai_agent.guardrails.web_search_query import (
    merge_query_with_hint,
    normalize_search_query,
    resolve_field_tokens,
    resolved_hint_has_unsubstituted_tokens,
    search_terms_from_context_hint,
)

_CITY_LINE_RE = re.compile(r"City of [A-Za-z][\w .-]+", re.IGNORECASE)

_PREFETCH_FIELD_CODES = (
    "GOVERNING_JURIS",
    "PROPERTY_ADDRESS",
    "PROPOSED_DEVELOPMENT",
    "WATERSHED_INFO",
    "TCAD_INFO",
    "IMPERVIOUS_REGS",
    "ZONING_REGS",
)


def _field_value(field_context: dict[str, str], code: str) -> str:
    return field_context.get(code, "").strip()


def _extract_city(blob: str) -> str:
    for line in blob.splitlines():
        match = _CITY_LINE_RE.search(line.strip())
        if match:
            city = match.group(0).strip()
            return city.split(",", maxsplit=1)[0].strip()
    return ""


def _resolved_hint_query(hint: str, field_context: dict[str, str]) -> str:
    resolved = resolve_field_tokens(hint, field_context).strip()
    if not resolved or resolved_hint_has_unsubstituted_tokens(resolved):
        return ""
    return normalize_search_query(resolved)


def derive_prefetch_queries(
    field_context: dict[str, str],
    *,
    search_context_hint: str = "",
    max_queries: int = 3,
) -> tuple[str, ...]:
    """Build deterministic prefetch queries before optional hybrid search."""
    queries: list[str] = []

    hint_query = _resolved_hint_query(search_context_hint, field_context)
    if hint_query:
        queries.append(hint_query)

    juris = _field_value(field_context, "GOVERNING_JURIS")
    address = _field_value(field_context, "PROPERTY_ADDRESS")
    zoning = _field_value(field_context, "ZONING_REGS")
    impervious = _field_value(field_context, "IMPERVIOUS_REGS")

    if impervious and juris:
        queries.append(normalize_search_query(f"{juris} impervious cover regulations {impervious}"))
    elif zoning and juris:
        queries.append(
            normalize_search_query(f"{juris} zoning district {zoning} development standards")
        )

    city = _extract_city(juris)
    if address and city:
        base = f"{city} development code site constraints {address}"
        queries.append(merge_query_with_hint(base, search_context_hint))

    if not queries and search_context_hint:
        terms = search_terms_from_context_hint(search_context_hint)
        if terms:
            queries.append(normalize_search_query(terms))

    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(q)
        if len(unique) >= max_queries:
            break

    return tuple(unique)
