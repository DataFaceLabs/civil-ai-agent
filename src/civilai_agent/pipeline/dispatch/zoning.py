"""Zoning branch dispatcher (Phase 3)."""

from __future__ import annotations

import json
import re
from typing import Any

from civilai_agent.pipeline.citations import build_citations_from_evidence
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


def _jurisdiction_det_inputs(ctx: SectionContext) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in _determination_items(ctx):
        if item.get("determination_id") in {"zoning_district", "permitting_authority"}:
            used = item.get("inputs_used")
            if isinstance(used, dict):
                merged.update(used)
    juris_section = ctx.related_facts.get("jurisdiction") if ctx.related_facts else None
    if isinstance(juris_section, dict):
        inner_j = juris_section.get("facts")
        if isinstance(inner_j, dict):
            for key, value in inner_j.items():
                merged.setdefault(f"jurisdiction.{key}", value)
    return merged


def _zoning_det_inputs(ctx: SectionContext) -> dict[str, Any]:
    for item in _determination_items(ctx):
        if item.get("determination_id") == "zoning_district":
            used = item.get("inputs_used")
            if isinstance(used, dict):
                return used
    return _jurisdiction_det_inputs(ctx)


def _municipality_unresolved(jctx: dict[str, Any]) -> bool:
    juris = (jctx.get("jurisdiction_primary") or "").lower()
    return "municipality unresolved" in juris or "municipality resolution" in juris


def _strip_misleading_austin_bootstrap(
    slots: dict[str, str | None],
    inner: dict[str, Any],
    jctx: dict[str, Any],
) -> None:
    """Drop Travis/COA bootstrap prose when jurisdiction facts name another county or are unresolved."""
    juris = (jctx.get("jurisdiction_primary") or "").lower()
    if "city of austin" in juris and "municipality unresolved" not in juris:
        return
    for key in ("impervious_regs", "compatibility_stds"):
        val = slots.get(key) or inner.get(key)
        if val and ("coa " in str(val).lower() or "city of austin" in str(val).lower()):
            slots[key] = None


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


def _overlays_present(raw: Any) -> bool:
    text = _normalize_code(raw)
    if not text or text == "[]":
        return False
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return True
    return bool(parsed)


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


def _county_non_zoning_confirmed(inner: dict[str, Any]) -> bool:
    """True only when governed data explicitly marks a confirmed non-zoning county."""
    flags = _parse_flags(inner.get("allowed_use_flags"))
    if "county_non_zoning_confirmed" in flags:
        return True
    raw = inner.get("non_zoning_county")
    return raw is True or (isinstance(raw, str) and raw.strip().lower() in {"true", "1", "yes"})


def _build_citations(facts_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    return build_citations_from_evidence(facts_payload)


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
        "impervious_regs": str(inner.get("impervious_regs"))
        if inner.get("impervious_regs") is not None
        else None,
        "compatibility_stds": str(inner.get("compatibility_stds"))
        if inner.get("compatibility_stds") is not None
        else None,
    }
    _strip_misleading_austin_bootstrap(slots, inner, jctx)

    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else {}
    citations = _build_citations(facts_payload)
    determinations = _relevant_determinations(ctx)
    missing_inputs: list[MissingInput] = []

    if _has_pending_flags(flags):
        if _municipality_unresolved(jctx):
            branch_id = "zoning.municipality_pending"
            county = _county_label(jctx.get("jurisdiction_primary") or "the")
            stems = [
                f"State that municipal limits and zoning district within {county} County "
                "are not resolved in governed data.",
                "Do not cite City of Austin or Travis County zoning unless jurisdiction "
                "facts establish that authority.",
                "Recommend municipal and county planning verification before asserting a "
                "zoning district or allowed uses.",
            ]
        else:
            branch_id = "zoning.pending"
            stems = [
                "State that zoning district lookup is pending or requires manual review.",
                "Do not assert that zoning does not apply or that the parcel is unzoned.",
            ]
        tier = 2
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
        if not _overlays_present(inner.get("overlays")):
            stems.append(
                "No zoning overlay district was identified in governed data for this base "
                "district; combining/overlay suffixes (e.g. -NP, -MU, -CO, -V) are not yet "
                "captured by the zoning connector. Do not state that no overlays apply — "
                "recommend verification with City of Austin zoning GIS."
            )
            missing_inputs.append(
                MissingInput(
                    name="zoning_overlays",
                    why_needed=(
                        "Combining/overlay districts materially change use and density rules "
                        "and are not captured by the current zoning connector."
                    ),
                    resolution="data-gap",
                )
            )
    elif _is_etj(jctx):
        branch_id = "zoning.etj"
        tier = 0
        city = _etj_city_label(juris or "the city")
        stems = [STEM_C_ETJ.format(city=city)]
    elif _is_county_jurisdiction(jctx):
        if not zoning_code and not _county_non_zoning_confirmed(inner):
            branch_id = "zoning.pending"
            tier = 2
            stems = [
                "State that the zoning district could not be confirmed from governed data alone.",
                "Do not assert that the county is non-zoning or that no municipal zoning applies "
                "without a verified zoning lookup.",
                "Recommend municipal and county planning verification before asserting allowed uses "
                "or rezoning requirements.",
            ]
        else:
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
