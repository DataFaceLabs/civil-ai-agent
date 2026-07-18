"""Generic dispatcher for descriptive sections (parcel, access).

These sections present governed facts under the tenant's subsection template rather than
rendering a safety-gated verdict (as zoning/flood do), so they need no per-section branch
logic: fetch the section facts + determinations, attach citations, and let the render path
lay them out under the tenant format directive. This replaces the expensive legacy tool
loop (~16-18k input tokens/draft, multi-turn) with a single render call (~3-5k) while
serving the same governed facts and citations -- the cost win from consolidating the last
legacy sections onto the common pipeline path.
"""

from __future__ import annotations

from typing import Any

from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.specs import DraftSpec


def _build_citations(facts_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Flatten the per-field ``evidence`` block into a compact citation list."""
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
            citations.append(
                {
                    "field": field,
                    "source_name": entry.get("source_name"),
                    "source_id": entry.get("source_id"),
                    "url": url,
                }
            )
    return citations


def _determinations(ctx: SectionContext) -> list[dict[str, Any]]:
    """All governed determinations for the entity (compliance risk, etc.).

    Descriptive sections draw on cross-cutting determinations (e.g. the parcel
    section's compliance-risk subsection), so unlike the branch dispatchers we keep the
    full set rather than filtering to a section-specific subset.
    """
    data = ctx.determinations
    if isinstance(data, dict):
        items = data.get("determinations")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def dispatch_descriptive(ctx: SectionContext, section_id: str) -> DraftSpec:
    """Map governed facts + determinations to a render-only DraftSpec (no branch logic)."""
    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else {}
    return DraftSpec(
        entity_id=ctx.entity_id,
        section_id=section_id,
        branch_id=f"{section_id}.render",
        tier=2,
        slots={},
        facts=facts_payload,
        determinations=_determinations(ctx),
        citations=_build_citations(facts_payload),
        stems=[],
        missing_inputs=[],
        searchable_gaps=[],
    )
