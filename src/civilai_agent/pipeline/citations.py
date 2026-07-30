"""Shared evidence → citation distillation for section draft dispatchers.

H1-PROV stamps ``as_of`` (value vintage) on section evidence; citation chips and
draft prompts need that vintage without shipping the raw evidence block twice.
"""

from __future__ import annotations

from typing import Any


def build_citations_from_evidence(facts_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Flatten per-field ``evidence`` into compact citation dicts.

    Includes ``as_of`` when present on an evidence entry (fact vintage / validity
    date — distinct from ``retrieved_at``).
    """
    if not isinstance(facts_payload, dict):
        return []
    evidence = facts_payload.get("evidence")
    if not isinstance(evidence, dict):
        return []
    citations: list[dict[str, Any]] = []
    for field, entries in evidence.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = entry.get("citation_url")
            if not url:
                continue
            citation: dict[str, Any] = {
                "field": field,
                "source_name": entry.get("source_name"),
                "source_id": entry.get("source_id"),
                "url": url,
            }
            as_of = entry.get("as_of")
            if as_of is not None and str(as_of).strip():
                citation["as_of"] = str(as_of).strip()
            retrieved_at = entry.get("retrieved_at")
            if retrieved_at is not None and str(retrieved_at).strip():
                citation["retrieved_at"] = str(retrieved_at).strip()
            citations.append(citation)
    return citations
