"""Zoning branch dispatcher (Phase 3)."""

from __future__ import annotations

import json
import re
from typing import Any

from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.specs import DraftSpec, MissingInput

_PENDING_FLAGS = frozenset({"zoning_lookup_pending", "manual_zoning_review_recommended"})

STEM_B_COUNTY = (
    "This property is located within the {county} County jurisdiction and is not subject "
    "to zoning regulations."
)
STEM_C_ETJ = "The property is within the ETJ of {city} and therefore has no zoning district."

_PROPOSED_USE_GAP = MissingInput(
    name="proposed_use",
    why_needed="A rezoning or use-permitted verdict requires the client's intended use.",
    resolution="client",
)


def _inner_facts(facts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(facts, dict):
        return {}
    inner = facts.get("facts")
    if isinstance(inner, dict):
        return inner
    return facts


def _normalize_code(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("null", "none"):
        return None
    return text


def _parse_flags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def _determination_items(ctx: SectionContext) -> list[dict[str, Any]]:
    data = ctx.determinations
    if isinstance(data, dict):
        items = data.get("determinations")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _zoning_det_inputs(ctx: SectionContext) -> dict[str, Any]:
    for item in _determination_items(ctx):
        if item.get("determination_id") == "zoning_district":
            used = item.get("inputs_used")
            if isinstance(used, dict):
                return used
    return {}


def _jurisdiction_context(ctx: SectionContext) -> dict[str, Any]:
    inputs = _zoning_det_inputs(ctx)
    inner = _inner_facts(ctx.facts)
    juris = inputs.get("jurisdiction.jurisdiction_primary") or inner.get("jurisdiction_primary")
    return {
        "jurisdiction_primary": str(juris).strip() if juris else None,
        "in_city_limits": inputs.get("jurisdiction.in_city_limits"),
        "in_etj": inputs.get("jurisdiction.in_etj"),
        "review_track": inputs.get("jurisdiction.review_track"),
    }


def _county_label(jurisdiction: str) -> str:
    match = re.match(r"^(.+?)\s+County", jurisdiction, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return jurisdiction.strip()


def _etj_city_label(jurisdiction: str) -> str:
    return re.sub(r"\s*\(ETJ\)\s*$", "", jurisdiction, flags=re.IGNORECASE).strip()


def _has_pending_flags(flags: list[str]) -> bool:
    return any(flag in _PENDING_FLAGS for flag in flags)


def _is_limited_purpose(jctx: dict[str, Any]) -> bool:
    if jctx.get("review_track") == "municipal_limited_purpose":
        return True
    juris = jctx.get("jurisdiction_primary") or ""
    return "limited" in juris.lower()


def _is_etj(jctx: dict[str, Any]) -> bool:
    if jctx.get("in_etj") is True:
        return True
    juris = jctx.get("jurisdiction_primary") or ""
    return "etj" in juris.lower()


def _is_county_jurisdiction(jctx: dict[str, Any]) -> bool:
    if jctx.get("review_track") == "county_baseline":
        return True
    juris = jctx.get("jurisdiction_primary") or ""
    lowered = juris.lower()
    return "county" in lowered and not lowered.startswith("city of")


def _build_citations(facts_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
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


def _relevant_determinations(ctx: SectionContext) -> list[dict[str, Any]]:
    zoning_ids = {"zoning_district", "permitting_authority"}
    return [
        item for item in _determination_items(ctx) if item.get("determination_id") in zoning_ids
    ]


def dispatch_zoning(ctx: SectionContext) -> DraftSpec:
    """Map governed zoning facts + determinations to a DraftSpec branch."""
    inner = _inner_facts(ctx.facts)
    flags = _parse_flags(inner.get("allowed_use_flags"))
    zoning_code = _normalize_code(inner.get("zoning_code"))
    zoning_base = inner.get("zoning_base")
    jctx = _jurisdiction_context(ctx)
    juris = jctx.get("jurisdiction_primary")

    slots: dict[str, str | None] = {
        "zoning_code": zoning_code,
        "zoning_base": str(zoning_base).strip() if zoning_base else None,
        "jurisdiction_primary": juris,
        "overlays": str(inner.get("overlays")) if inner.get("overlays") is not None else None,
        "review_track": (
            str(jctx["review_track"]) if jctx.get("review_track") is not None else None
        ),
    }

    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else {}
    citations = _build_citations(facts_payload)
    determinations = _relevant_determinations(ctx)
    missing_inputs: list[MissingInput] = []

    if _has_pending_flags(flags):
        branch_id = "zoning.pending"
        tier = 2
        stems = [
            "State that zoning district lookup is pending or requires manual review.",
            "Do not assert that zoning does not apply or that the parcel is unzoned.",
        ]
    elif zoning_code:
        if _is_limited_purpose(jctx):
            branch_id = "zoning.coa_limited_purpose"
            stems = [
                f"Lead with the zoning designation {zoning_code}"
                + (f" ({zoning_base})" if zoning_base else "")
                + ".",
                "State clearly that municipal zoning applies under limited-purpose jurisdiction.",
                "Do not assert that zoning does not apply.",
            ]
        else:
            branch_id = "zoning.zoned_city"
            stems = [
                "According to information provided, identify the zoning district "
                "from governed facts.",
                "List overlays only when present in governed facts.",
                "Do not emit a rezoning verdict; proposed use is not specified.",
            ]
        tier = 2
        missing_inputs = [_PROPOSED_USE_GAP]
    elif _is_etj(jctx):
        branch_id = "zoning.etj"
        tier = 0
        city = _etj_city_label(juris or "the city")
        stems = [STEM_C_ETJ.format(city=city)]
    elif _is_county_jurisdiction(jctx):
        branch_id = "zoning.county_no_zoning"
        tier = 0
        county = _county_label(juris or "the")
        stems = [STEM_B_COUNTY.format(county=county)]
    else:
        branch_id = "zoning.pending"
        tier = 2
        stems = [
            "State that zoning could not be resolved from governed data alone.",
            "Recommend manual zoning verification; do not assert zoning does not apply.",
        ]

    return DraftSpec(
        entity_id=ctx.entity_id,
        section_id="zoning",
        branch_id=branch_id,
        tier=tier,
        slots=slots,
        facts=facts_payload,
        determinations=determinations,
        citations=citations,
        stems=stems,
        missing_inputs=missing_inputs,
        searchable_gaps=[],
    )
