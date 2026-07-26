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

from civilai_agent.pipeline.citations import build_citations_from_evidence
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.specs import DraftSpec


def _build_citations(facts_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Flatten the per-field ``evidence`` block into a compact citation list."""
    return build_citations_from_evidence(facts_payload)


def _inner_facts(facts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(facts, dict):
        return {}
    inner = facts.get("facts")
    if isinstance(inner, dict):
        return inner
    return facts


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("null", "none"):
        return None
    return text


def _float_value(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _access_stems(inner: dict[str, Any]) -> list[str]:
    """ROW / ASMP stems when mobility facts are present (access section)."""
    stems: list[str] = []
    row_existing = _float_value(inner.get("row_existing_ft"))
    row_required = _float_value(inner.get("row_required_ft"))
    asmp = _normalize_text(inner.get("asmp_level"))
    if row_existing is not None or row_required is not None:
        parts: list[str] = []
        if row_existing is not None:
            parts.append(f"existing ROW ≈ {row_existing:g} ft")
        if row_required is not None:
            parts.append(f"required ROW ≈ {row_required:g} ft")
        stems.append(
            "Right-of-way from governed mobility facts: "
            + "; ".join(parts)
            + ". Do not invent dedication widths beyond these values."
        )
    if asmp:
        stems.append(
            f"ASMP / roadway classification level from governed facts: {asmp}. "
            "Confirm frontage and access spacing against the jurisdiction ASMP map."
        )
    return stems


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
    stems: list[str] = []
    if section_id in {"access", "mobility"}:
        stems = _access_stems(_inner_facts(facts_payload))
    return DraftSpec(
        entity_id=ctx.entity_id,
        section_id=section_id,
        branch_id=f"{section_id}.render",
        tier=2,
        slots={},
        facts=facts_payload,
        determinations=_determinations(ctx),
        citations=_build_citations(facts_payload),
        stems=stems,
        missing_inputs=[],
        searchable_gaps=[],
    )
