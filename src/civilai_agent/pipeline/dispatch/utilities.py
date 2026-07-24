"""Utilities branch dispatcher (Phase 5)."""

from __future__ import annotations

from typing import Any

from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.quality_flags import ccn_provider_confirmed
from civilai_agent.pipeline.specs import DraftSpec, MissingInput

_PROVIDER_UNCONFIRMED_GAP = MissingInput(
    name="utility_provider_ccn",
    why_needed=(
        "Utility provider identity requires CCN overlay confirmation; baseline inference "
        "alone is not sufficient to name a provider."
    ),
    resolution="data-gap",
)

_WW_DISTANCE_OSSF_THRESHOLD_FT = 500.0
_METERS_TO_FEET = 3.280839895

_COVERAGE_DISCLAIMER_STEM = (
    "Service territory or CCN coverage indicates the provider could serve the area; "
    "it does not confirm capacity, connection point, or will-serve."
)

_LINE_GIS_DISCLAIMER_STEM = (
    "GIS nearest-main distance/diameter is proximity evidence only — not a connection "
    "point, capacity, or will-serve commitment."
)

_TAP_CARDS_DISCLAIMER_STEM = (
    "Municipal tap cards are historical connection records; they do not prove current "
    "capacity or will-serve."
)

_WW_DISTANCE_GAP = MissingInput(
    name="ww_main_distance_ft",
    why_needed=(
        "Distance to the nearest wastewater main determines SER feasibility vs OSSF fallback."
    ),
    resolution="data-gap",
)

_PROPOSED_USE_GAP = MissingInput(
    name="proposed_use",
    why_needed="Utility demand and connection standards depend on the client's intended use.",
    resolution="client",
)


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


def _bool_value(raw: Any) -> bool | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in ("true", "yes", "1"):
            return True
        if lowered in ("false", "no", "0"):
            return False
    return None


def _float_value(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _distance_ft_from_facts(inner: dict[str, Any], *, kind: str) -> float | None:
    """Prefer lake nearest_*_distance_m (meters); fall back to legacy *_ft keys."""
    meters = _float_value(inner.get(f"nearest_{kind}_distance_m"))
    if meters is not None:
        return meters * _METERS_TO_FEET
    legacy = _float_value(
        inner.get(f"{'ww' if kind == 'wastewater' else 'water'}_main_distance_ft")
    )
    if legacy is not None:
        return legacy
    return _float_value(inner.get(f"nearest_{kind}_distance_ft"))


def _has_tap_cards(inner: dict[str, Any]) -> bool:
    raw = inner.get("tap_cards_json")
    if raw is None:
        return False
    if isinstance(raw, list):
        return len(raw) > 0
    text = str(raw).strip()
    return bool(text) and text not in ("[]", "{}", "null", "None")


def _determination_items(ctx: SectionContext) -> list[dict[str, Any]]:
    data = ctx.determinations
    if isinstance(data, dict):
        items = data.get("determinations")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _relevant_determinations(ctx: SectionContext) -> list[dict[str, Any]]:
    util_ids = {
        "wastewater_service",
        "water_service",
        "fire_protection",
        "ossf_lot_size_feasibility",
    }
    return [item for item in _determination_items(ctx) if item.get("determination_id") in util_ids]


def _det_conclusion(ctx: SectionContext, determination_id: str) -> str | None:
    for item in _determination_items(ctx):
        if item.get("determination_id") == determination_id:
            return _normalize_text(item.get("conclusion"))
    return None


def _build_citations(facts_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(facts_payload, dict):
        return []
    evidence = facts_payload.get("evidence")
    citations: list[dict[str, Any]] = []
    if isinstance(evidence, dict):
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
    citations.extend(_gis_viewer_citations(_inner_facts(facts_payload)))
    return citations


_GIS_VIEWER_LABELS: tuple[tuple[str, str], ...] = (
    ("water", "Nearest water main"),
    ("wastewater", "Nearest wastewater main"),
)


def _gis_viewer_citations(inner: dict[str, Any]) -> list[dict[str, Any]]:
    """Map Viewer deep links from overlay facts (friendly labels for draft HREFs)."""
    out: list[dict[str, Any]] = []
    for kind, label in _GIS_VIEWER_LABELS:
        href = _normalize_text(inner.get(f"nearest_{kind}_drawing_href"))
        if not href or "apps/mapviewer" not in href:
            continue
        out.append(
            {
                "field": f"nearest_{kind}_drawing_href",
                "source_name": label,
                "source_id": f"agol_map_viewer_{kind}",
                "url": href,
            }
        )
    return out


def _sanitize_provider_slots(
    slots: dict[str, str | None],
    facts_payload: dict[str, Any],
) -> list[MissingInput]:
    """Drop provider names from render slots when CCN overlay did not confirm them."""
    gaps: list[MissingInput] = []
    mapping = (
        ("water_provider", "water"),
        ("wastewater_provider", "wastewater"),
        ("power_provider", "electric"),
    )
    for slot_key, kind in mapping:
        if slots.get(slot_key) and not ccn_provider_confirmed(facts_payload, kind):
            slots[slot_key] = None
            gaps.append(_PROVIDER_UNCONFIRMED_GAP)
    return gaps


def dispatch_utilities(ctx: SectionContext) -> DraftSpec:
    """Map governed utilities facts to a DraftSpec branch."""
    inner = _inner_facts(ctx.facts)
    ossf_required = _bool_value(inner.get("ossf_required"))
    ossf_existing_retained = _bool_value(inner.get("ossf_existing_retained"))
    water_provider = _normalize_text(inner.get("water_provider"))
    wastewater_provider = _normalize_text(inner.get("wastewater_provider"))
    power_provider = _normalize_text(inner.get("power_provider"))
    ww_distance = _distance_ft_from_facts(inner, kind="wastewater")
    water_distance = _distance_ft_from_facts(inner, kind="water")
    coverage_tier = _normalize_text(inner.get("network_coverage_tier"))
    ossf_authority = _normalize_text(inner.get("ossf_authority"))
    esd_name = _normalize_text(inner.get("esd_name"))

    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else {}
    ossf_lot_size_conclusion = _det_conclusion(ctx, "ossf_lot_size_feasibility")
    slots: dict[str, str | None] = {
        "ossf_required": None if ossf_required is None else str(ossf_required).lower(),
        "ossf_existing_retained": None
        if ossf_existing_retained is None
        else str(ossf_existing_retained).lower(),
        "water_provider": water_provider,
        "wastewater_provider": wastewater_provider,
        "power_provider": power_provider,
        "ww_main_distance_ft": None if ww_distance is None else str(ww_distance),
        "water_main_distance_ft": None if water_distance is None else str(water_distance),
        "network_coverage_tier": coverage_tier,
        "ossf_authority": ossf_authority,
        "esd_name": esd_name,
    }

    missing_inputs: list[MissingInput] = [_PROPOSED_USE_GAP]
    stems: list[str] = [
        _COVERAGE_DISCLAIMER_STEM,
        "Draft Water, Wastewater, Electric, and Fire Protection subsections when facts support them.",
        "Never assert water or wastewater is available from territory/CCN coverage alone.",
    ]
    if coverage_tier == "line_gis" or ww_distance is not None or water_distance is not None:
        stems.append(_LINE_GIS_DISCLAIMER_STEM)
    if coverage_tier == "unknown":
        stems.append(
            "Municipal line GIS coverage is unknown for this parcel — do not invent nearest-main "
            "distance or diameter."
        )
    if _has_tap_cards(inner):
        stems.append(_TAP_CARDS_DISCLAIMER_STEM)

    if ossf_required is True:
        branch_id = "utilities.ossf"
        stems.extend(
            [
                "State that centralized wastewater is not available; OSSF/septic is required.",
                "Identify OSSF permitting authority from governed facts when present.",
                "Note lot-size feasibility depends on parcel area and system type (advanced ≥1.0 ac, "
                "conventional ≥1.5 ac) when applicable.",
            ]
        )
        if ossf_authority is None:
            missing_inputs.append(
                MissingInput(
                    name="ossf_authority",
                    why_needed="OSSF permits are issued by a specific authority.",
                    resolution="records",
                )
            )
    elif (
        wastewater_provider
        and ww_distance is not None
        and ww_distance >= _WW_DISTANCE_OSSF_THRESHOLD_FT
    ):
        branch_id = "utilities.provider_distant"
        stems.extend(
            [
                f"Wastewater main is approximately {ww_distance:.0f} ft from the property.",
                "Do NOT state that centralized sewer is available or that OSSF is not required "
                "without provider SER/will-serve analysis.",
                "Discuss OSSF/septic as the likely path when main distance is prohibitive; "
                "SER feasibility is not established from distance alone.",
            ]
        )
        missing_inputs.append(_WW_DISTANCE_GAP)
    elif wastewater_provider and ww_distance is not None and ww_distance > 100:
        branch_id = "utilities.provider_distant"
        stems.extend(
            [
                f"Name wastewater provider {wastewater_provider} but note main is ~{ww_distance:.0f} ft away.",
                "Discuss SER (service extension request) vs OSSF fallback; do not recommend SER as feasible "
                "without provider analysis when distance is large.",
            ]
        )
    elif wastewater_provider and ossf_required is False:
        branch_id = "utilities.public_main"
        stems.extend(
            [
                "Centralized wastewater may apply when provider and main distance are confirmed.",
                "Do NOT state OSSF is not required when main distance is unconfirmed.",
                "Describe connection standards only when governed facts support them.",
            ]
        )
        if ww_distance is None:
            missing_inputs.append(_WW_DISTANCE_GAP)
            stems.append(
                "Distance to nearest wastewater main is not documented — do NOT assert "
                "centralized sewer feasibility or that OSSF is not required."
            )
    elif wastewater_provider:
        branch_id = "utilities.public_main"
        stems.append(
            f"Name provider {wastewater_provider}; confirm connection distance with provider maps."
        )
        missing_inputs.append(_WW_DISTANCE_GAP)
    else:
        branch_id = "utilities.ossf"
        stems.extend(
            [
                "No public wastewater provider identified; proceed to OSSF branch.",
                "Do not claim centralized sewer availability.",
            ]
        )

    if water_provider and ccn_provider_confirmed(facts_payload, "water"):
        if water_distance is not None:
            stems.append(
                f"Potable water provider from governed CCN facts: {water_provider}; "
                f"nearest water main ≈ {water_distance:.0f} ft (GIS proximity only)."
            )
        else:
            stems.append(f"Potable water provider from governed CCN facts: {water_provider}.")
    elif water_provider:
        stems.append("Potable water provider is pending CCN confirmation — do NOT name a provider.")
        missing_inputs.append(_PROVIDER_UNCONFIRMED_GAP)
    else:
        missing_inputs.append(
            MissingInput(
                name="water_provider",
                why_needed="Potable water provider must be identified for the Water Service subsection.",
                resolution="records",
            )
        )

    if power_provider and ccn_provider_confirmed(facts_payload, "electric"):
        stems.append(
            f"Electric provider from governed CCN facts: {power_provider}. "
            "Do not default to Austin Energy unless governed facts confirm it."
        )
    elif power_provider:
        stems.append(
            "Electric provider is pending CCN confirmation — do NOT name a provider "
            "(do not default to Austin Energy)."
        )
        missing_inputs.append(_PROVIDER_UNCONFIRMED_GAP)
    else:
        missing_inputs.append(
            MissingInput(
                name="power_provider",
                why_needed="Electric provider must be identified for the Electric Service subsection.",
                resolution="records",
            )
        )

    if esd_name:
        stems.append(f"Fire protection district: {esd_name}.")

    for kind, label in _GIS_VIEWER_LABELS:
        href = _normalize_text(inner.get(f"nearest_{kind}_drawing_href"))
        if href and "apps/mapviewer" in href:
            stems.append(
                f"Include the GIS viewer link as markdown [{label}]({href}) in the "
                f"relevant {kind} subsection."
            )

    if ossf_lot_size_conclusion and (
        ossf_required is True or branch_id == "utilities.ossf" or ossf_existing_retained is not None
    ):
        stems.append(f"OSSF lot-size feasibility: {ossf_lot_size_conclusion}")
    elif ossf_required is True and ossf_existing_retained is None:
        missing_inputs.append(
            MissingInput(
                name="ossf_existing_retained",
                why_needed=(
                    "Whether an existing OSSF is retained affects minimum lot-size gate "
                    "applicability for replatted developed lots."
                ),
                resolution="records",
            )
        )

    ccn_gaps = _sanitize_provider_slots(slots, facts_payload)
    missing_inputs.extend(g for g in ccn_gaps if g not in missing_inputs)

    return DraftSpec(
        entity_id=ctx.entity_id,
        section_id="utilities",
        branch_id=branch_id,
        tier=2,
        slots=slots,
        facts=facts_payload,
        determinations=_relevant_determinations(ctx),
        citations=_build_citations(facts_payload),
        stems=stems,
        missing_inputs=missing_inputs,
        searchable_gaps=[],
    )
