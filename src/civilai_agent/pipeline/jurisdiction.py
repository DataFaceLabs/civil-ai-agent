"""Jurisdiction context for provenance-gated env/flood/zoning dispatch."""

from __future__ import annotations

from typing import Any

from civilai_agent.pipeline.fetch import SectionContext


def _inner_facts(facts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(facts, dict):
        return {}
    inner = facts.get("facts")
    if isinstance(inner, dict):
        return inner
    return facts


def _determination_items(ctx: SectionContext) -> list[dict[str, Any]]:
    data = ctx.determinations
    if isinstance(data, dict):
        items = data.get("determinations")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _jurisdiction_det_inputs(ctx: SectionContext) -> dict[str, Any]:
    for item in _determination_items(ctx):
        if item.get("determination_id") in ("jurisdiction", "zoning_district"):
            used = item.get("inputs_used")
            if isinstance(used, dict):
                return used
    return {}


def jurisdiction_context(ctx: SectionContext) -> dict[str, Any]:
    """Merge jurisdiction section facts (when fetched) with determination inputs."""
    inputs = _jurisdiction_det_inputs(ctx)
    inner: dict[str, Any] = {}
    juris_section = ctx.related_facts.get("jurisdiction") if ctx.related_facts else None
    if isinstance(juris_section, dict):
        inner = _inner_facts(juris_section)

    juris = (
        inputs.get("jurisdiction.jurisdiction_primary")
        or inner.get("jurisdiction_primary")
        or inputs.get("jurisdiction_primary")
    )
    in_city = inputs.get("jurisdiction.in_city_limits")
    if in_city is None:
        in_city = inner.get("in_city_limits")
    in_etj = inputs.get("jurisdiction.in_etj")
    if in_etj is None:
        in_etj = inner.get("in_etj")
    review_track = inputs.get("jurisdiction.review_track") or inner.get("review_track")

    return {
        "jurisdiction_primary": str(juris).strip() if juris else None,
        "in_city_limits": in_city,
        "in_etj": in_etj,
        "review_track": review_track,
    }


def _is_city_of_austin(jctx: dict[str, Any]) -> bool:
    juris = (jctx.get("jurisdiction_primary") or "").lower()
    return "city of austin" in juris and "municipality unresolved" not in juris


def _is_travis_unincorporated(jctx: dict[str, Any]) -> bool:
    juris = (jctx.get("jurisdiction_primary") or "").lower()
    in_city = jctx.get("in_city_limits")
    return "travis county" in juris and in_city is not True and "municipality unresolved" not in juris


def requires_local_municipal_playbook(jctx: dict[str, Any]) -> bool:
    """Non-CoA municipal full-purpose cities (Elgin, Kyle, etc.) — not Travis/COA templates."""
    if _is_city_of_austin(jctx):
        return False
    if _is_travis_unincorporated(jctx):
        return False
    return jctx.get("in_city_limits") is True


def local_municipality_label(jctx: dict[str, Any]) -> str:
    juris = jctx.get("jurisdiction_primary") or "the local municipality"
    return str(juris).strip()
