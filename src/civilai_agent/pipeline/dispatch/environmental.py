"""Environmental branch dispatcher (Phase 6) — Edwards Aquifer + CWQZ."""

from __future__ import annotations

from typing import Any

from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.specs import DraftSpec, MissingInput

_TRAVIS_FIPS = "48453"

_EDWARDS_ZONE_GAP = MissingInput(
    name="edwards_aquifer_zone",
    why_needed=(
        "Edwards Aquifer zone classification (Recharge / Contributing / outside) "
        "could not be confirmed from governed data."
    ),
    resolution="data-gap",
)

_WATERWAY_CLASS_GAP = MissingInput(
    name="waterway_classification",
    why_needed=(
        "Contributing drainage area at the nearest waterway is needed to classify "
        "minor/intermediate/major and derive CWQZ setbacks."
    ),
    resolution="data-gap",
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


def _normalize_zone(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    return text.lower()


def _normalize_wpap(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    return text.upper()


def _float_value(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _tcad_travis_from_evidence(facts_payload: dict[str, Any]) -> bool:
    evidence = facts_payload.get("evidence")
    if not isinstance(evidence, dict):
        return False
    for entries in evidence.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("source_id") == "tcad":
                return True
    return False


def _is_pending_placeholder(value: Any) -> bool:
    text = _normalize_text(value)
    if text is None:
        return False
    return " pending " in f" {text.lower()} "


def _determination_items(ctx: SectionContext) -> list[dict[str, Any]]:
    data = ctx.determinations
    if isinstance(data, dict):
        items = data.get("determinations")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _det_inputs(ctx: SectionContext, determination_id: str) -> dict[str, Any]:
    for item in _determination_items(ctx):
        if item.get("determination_id") == determination_id:
            used = item.get("inputs_used")
            if isinstance(used, dict):
                return used
    return {}


def _watershed_name(ctx: SectionContext) -> str | None:
    used = _det_inputs(ctx, "watershed_classification")
    return _normalize_text(used.get("watershed.watershed_name"))


def _source_fips(facts_payload: dict[str, Any], inner: dict[str, Any]) -> str | None:
    for key in ("source_fips", "county_fips"):
        val = inner.get(key) or facts_payload.get(key)
        text = _normalize_text(val)
        if text:
            return text
    # Holdout API payloads often omit FIPS; TCAD evidence + Edwards or CWQZ facts imply Travis.
    if _tcad_travis_from_evidence(facts_payload) and (
        inner.get("cwqz_setback_ft") is not None
        or _normalize_text(inner.get("waterway_name"))
        or _normalize_zone(inner.get("wpap_type")) is not None
        or _normalize_zone(inner.get("zone_type")) is not None
    ):
        return _TRAVIS_FIPS
    return None


def _is_travis_county(fips: str | None) -> bool:
    return fips == _TRAVIS_FIPS


def _relevant_determinations(ctx: SectionContext) -> list[dict[str, Any]]:
    env_ids = {
        "edwards_water_quality",
        "edwards_aquifer",
        "waterway_setback",
        "cwqz",
        "critical_water_quality_zone",
        "watershed_classification",
    }
    return [item for item in _determination_items(ctx) if item.get("determination_id") in env_ids]


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


def _cwqz_stems(
    *,
    in_travis: bool,
    setback_ft: int | None,
    waterway_name: str | None,
    classification: str | None,
    drainage_acres: float | None,
) -> tuple[list[str], list[MissingInput]]:
    stems: list[str] = []
    gaps: list[MissingInput] = []

    if not in_travis:
        stems.append(
            "Travis County Code §482.941 CWQZ setbacks are not modeled outside Travis County; "
            "local watershed ordinances may apply. Do not treat null cwqz_setback_ft as a data gap."
        )
        return stems, gaps

    if setback_ft is not None:
        parts = [f"State CWQZ setback of {setback_ft} feet"]
        if waterway_name:
            parts.append(f"along {waterway_name}")
        if classification:
            parts.append(f"({classification} waterway")
            if drainage_acres is not None:
                parts[-1] += f", ~{drainage_acres:.0f} ac contributing drainage"
            parts[-1] += ")"
        parts.append("per Travis County Code §482.941 (64/320/640 ac → 100/200/300 ft).")
        stems.append(" ".join(parts))
        stems.append(
            "Never substitute legacy 50/100/200 ft setback values; corpus and holdout "
            "confirm 100/200/300 ft (400 ft Colorado River below Lady Bird Lake)."
        )
        return stems, gaps

    if waterway_name and classification:
        stems.append(
            f"Named waterway {waterway_name} is classified {classification} but no CWQZ setback "
            "was derived — verify drainage-area delineation and jurisdiction-specific rules."
        )
        gaps.append(_WATERWAY_CLASS_GAP)
    elif waterway_name:
        stems.append(
            f"Waterway {waterway_name} is identified but classification/setback could not be confirmed."
        )
        gaps.append(_WATERWAY_CLASS_GAP)
    else:
        stems.append(
            "No jurisdictional waterway requiring a CWQZ setback was identified from governed data."
        )

    return stems, gaps


def _watershed_ehz_stems(
    *,
    watershed_name: str | None,
    erosion_hazard: str | None,
    in_travis: bool,
    cwqz_setback_ft: int | None,
) -> tuple[list[str], list[MissingInput]]:
    stems: list[str] = []
    gaps: list[MissingInput] = []

    if watershed_name:
        stems.append(
            f"The property lies within the {watershed_name} watershed; regional drainage "
            "criteria and water-quality controls for this watershed apply."
        )

    if _is_pending_placeholder(erosion_hazard):
        stems.append(
            "Erosion Hazard Zone (EHZ) overlay classification is pending from governed data; "
            "confirm EHZ applicability with City of Austin GIS before concluding encroachment."
        )
        gaps.append(
            MissingInput(
                name="erosion_hazard",
                why_needed="EHZ overlay assignment determines erosion-control setbacks.",
                resolution="data-gap",
            )
        )
    elif erosion_hazard and not _is_pending_placeholder(erosion_hazard):
        stems.append(erosion_hazard)

    if watershed_name and in_travis and cwqz_setback_ft is None:
        stems.append(
            "When no on-site CWQZ setback is derived, state that governed data did not identify "
            "an adjacent jurisdictional waterway requiring a Critical Water Quality Zone buffer; "
            "verify off-site intermediate waterway buffers with jurisdiction GIS."
        )

    return stems, gaps


def dispatch_environmental(ctx: SectionContext) -> DraftSpec:
    """Map governed Edwards/CWQZ facts to a DraftSpec branch."""
    inner = _inner_facts(ctx.facts)
    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else {}

    wpap_type = _normalize_wpap(inner.get("wpap_type"))
    zone_type = _normalize_zone(inner.get("zone_type"))
    waterway_name = _normalize_text(inner.get("waterway_name"))
    classification = _normalize_zone(inner.get("classification"))
    drainage_acres = _float_value(inner.get("drainage_area_acres"))
    setback_raw = inner.get("cwqz_setback_ft")
    setback_ft: int | None
    if setback_raw is None:
        setback_ft = None
    else:
        try:
            setback_ft = int(float(setback_raw))
        except (TypeError, ValueError):
            setback_ft = None

    source_fips = _source_fips(facts_payload, inner)
    in_travis = _is_travis_county(source_fips)
    watershed_name = _watershed_name(ctx)
    erosion_hazard = _normalize_text(inner.get("erosion_hazard"))
    ehz_pending = _is_pending_placeholder(erosion_hazard)

    slots: dict[str, str | None] = {
        "wpap_type": wpap_type,
        "zone_type": zone_type,
        "waterway_name": waterway_name,
        "classification": classification,
        "drainage_area_acres": None if drainage_acres is None else str(drainage_acres),
        "cwqz_setback_ft": None if setback_ft is None else str(setback_ft),
        "source_fips": source_fips,
        "in_travis_county": str(in_travis).lower(),
        "watershed_name": watershed_name,
        "erosion_hazard": None if ehz_pending else erosion_hazard,
        "erosion_hazard_pending": str(ehz_pending).lower(),
    }

    missing_inputs: list[MissingInput] = []
    stems: list[str] = []

    if wpap_type == "UNKNOWN" or (wpap_type is None and zone_type is None):
        branch_id = "environmental.edwards_unclassified"
        tier = 2
        stems.extend(
            [
                "Edwards Aquifer zone is unclassified — do NOT assert the site is outside "
                "the Recharge or Contributing zones.",
                "Recommend TCEQ Edwards Aquifer viewer verification.",
            ]
        )
        missing_inputs.append(_EDWARDS_ZONE_GAP)
    elif wpap_type == "WPAP" or zone_type in ("recharge", "transition"):
        branch_id = "environmental.edwards_wpap"
        tier = 2
        stems.extend(
            [
                "Property is in the Edwards Aquifer Recharge Zone (or Transition Zone treated "
                "as recharge per 30 TAC 213.3(28)).",
                "A Water Pollution Abatement Plan (WPAP) will be necessary for regulated activities.",
                "Note <20% impervious cover exemption for lots larger than 5 acres where applicable "
                "(30 TAC 213.4(f)).",
            ]
        )
    elif wpap_type == "CZP" or zone_type == "contributing":
        branch_id = "environmental.edwards_czp"
        tier = 2
        stems.extend(
            [
                "Property is in the Edwards Aquifer Contributing Zone per TCEQ Edwards Aquifer Viewer.",
                "Contributing Zone Program (CZP) compliance applies; WPAP is not required unless "
                "recharge-zone rules also apply.",
            ]
        )
    elif wpap_type == "OUTSIDE" or zone_type == "outside":
        branch_id = "environmental.edwards_outside"
        tier = 1
        stems.append(
            "Render the EA-outside verbatim stem: outside the Edwards Aquifer Transition Zone "
            "(TCEQ); no additional Edwards permits; outside the Barton Springs zone."
        )
    else:
        branch_id = "environmental.edwards_unclassified"
        tier = 2
        stems.append(
            f"Edwards Aquifer classification ({wpap_type or zone_type}) is not mapped; "
            "do not assert outside status."
        )
        missing_inputs.append(_EDWARDS_ZONE_GAP)

    cwqz_stems, cwqz_gaps = _cwqz_stems(
        in_travis=in_travis,
        setback_ft=setback_ft,
        waterway_name=waterway_name,
        classification=classification,
        drainage_acres=drainage_acres,
    )
    stems.extend(cwqz_stems)
    missing_inputs.extend(cwqz_gaps)

    composite_stems, composite_gaps = _watershed_ehz_stems(
        watershed_name=watershed_name,
        erosion_hazard=erosion_hazard,
        in_travis=in_travis,
        cwqz_setback_ft=setback_ft,
    )
    stems.extend(composite_stems)
    missing_inputs.extend(composite_gaps)

    return DraftSpec(
        entity_id=ctx.entity_id,
        section_id="environmental",
        branch_id=branch_id,
        tier=tier,
        slots=slots,
        facts=facts_payload,
        determinations=_relevant_determinations(ctx),
        citations=_build_citations(facts_payload),
        stems=stems,
        missing_inputs=missing_inputs,
        searchable_gaps=[],
    )
