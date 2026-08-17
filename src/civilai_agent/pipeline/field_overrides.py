"""Overlay workbench field_context onto lake SectionContext before drafting.

After Accept Zone Change (or any analyst jurisdiction edit), the FE sends updated
GOVERNING_JURIS / permitting fields in field_context. The draft pipeline still
fetches lake facts + determinations by entity_id — those remain the *original*
jurisdiction. Prefer workbench values so parcel/zoning drafts cannot resurrect
stale ETJ framing.
"""

from __future__ import annotations

from typing import Any

from civilai_agent.pipeline.fetch import SectionContext

# FE codes → lake fact / determination input keys that must stay aligned.
_FE_TO_LAKE_FACT: dict[str, tuple[str, ...]] = {
    "GOVERNING_JURIS": ("jurisdiction_primary",),
    "ZONING_REGS": ("zoning_code", "zoning_base"),
    "PROPERTY_ADDRESS": ("property_address", "situs_address"),
    "PERMITTING_AUTHORITY_DETAIL": ("review_track",),
}

_JURISDICTION_FE_CODES = frozenset(
    {
        "GOVERNING_JURIS",
        "PERMITTING_AUTHORITY_DETAIL",
        "JURISDICTION_STATUS",
        "LDC_REFERENCE",
    }
)

# CAD appraisal columns leak into Parcel drafts via parcel-overview lake facts even
# when Prompt Lab field_context omitted them. Keep each key only when field_context
# carries that lake key or the FE compose code that surfaces it.
_PARCEL_APPRAISAL_FACT_ALLOW: dict[str, frozenset[str]] = {
    "market_value_usd": frozenset({"market_value_usd", "CAD_VALUATION", "TCAD_VALUATION"}),
    "land_value_usd": frozenset({"land_value_usd", "CAD_VALUATION", "TCAD_VALUATION"}),
    "improvement_value_usd": frozenset(
        {"improvement_value_usd", "CAD_VALUATION", "TCAD_VALUATION"}
    ),
    "living_area_sqft": frozenset({"living_area_sqft", "BUILDING_DETAIL"}),
}
_PARCEL_APPRAISAL_LAKE_KEYS = tuple(_PARCEL_APPRAISAL_FACT_ALLOW)
_PARCEL_SECTION_IDS = frozenset({"parcel", "parcel-overview"})


def _inner_facts(facts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(facts, dict):
        return {}
    inner = facts.get("facts")
    if isinstance(inner, dict):
        return dict(inner)
    return dict(facts)


def _with_inner_facts(facts: dict[str, Any] | None, inner: dict[str, Any]) -> dict[str, Any]:
    if isinstance(facts, dict) and isinstance(facts.get("facts"), dict):
        return {**facts, "facts": inner}
    return inner


def _determination_items(
    determinations: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(determinations, dict):
        return []
    items = determinations.get("determinations")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _rewrite_determinations(
    determinations: dict[str, Any] | None,
    *,
    governing: str,
    permitting: str,
) -> dict[str, Any] | None:
    """Rewrite jurisdiction determination inputs/conclusions to match workbench values."""
    items = _determination_items(determinations)
    if not items:
        return determinations

    governing_l = governing.lower()
    looks_etj = "etj" in governing_l or "extraterritorial" in governing_l
    # Accept Zone Change often stamps a short place label ("Georgetown") rather than
    # "City of Georgetown". Any non-ETJ workbench override should clear lake ETJ flags.
    looks_city = bool(governing) and not looks_etj

    rewritten: list[dict[str, Any]] = []
    changed = False
    for item in items:
        det_id = str(item.get("determination_id") or "")
        if det_id not in {
            "jurisdiction",
            "zoning_district",
            "required_permits",
            "permit_contacts",
        }:
            rewritten.append(item)
            continue
        next_item = dict(item)
        inputs = item.get("inputs_used")
        if isinstance(inputs, dict) or governing:
            next_inputs = dict(inputs) if isinstance(inputs, dict) else {}
            if governing:
                for key in (
                    "jurisdiction.jurisdiction_primary",
                    "jurisdiction_primary",
                ):
                    if (
                        key in next_inputs
                        or det_id == "jurisdiction"
                        or not isinstance(inputs, dict)
                    ):
                        next_inputs[key] = governing
                        changed = True
                if looks_city or looks_etj or "jurisdiction.in_etj" in next_inputs:
                    next_inputs["jurisdiction.in_etj"] = looks_etj
                    changed = True
                if looks_city or looks_etj or "jurisdiction.in_city_limits" in next_inputs:
                    next_inputs["jurisdiction.in_city_limits"] = looks_city
                    changed = True
            if permitting and (
                "jurisdiction.review_track" in next_inputs or det_id == "jurisdiction"
            ):
                next_inputs["jurisdiction.review_track"] = permitting
                changed = True
            next_item["inputs_used"] = next_inputs
        conclusion = str(item.get("conclusion") or "")
        if (
            governing
            and conclusion
            and ("etj" in conclusion.lower() or "extraterritorial" in conclusion.lower())
        ):
            # Drop stale ETJ conclusions when the workbench jurisdiction changed;
            # the renderer should use workbench field values + rewritten inputs.
            next_item["conclusion"] = (
                f"Workbench jurisdiction override: {governing}. "
                "Confirm permitting track against the governing jurisdiction records."
            )
            changed = True
        elif governing and det_id == "jurisdiction" and not conclusion.strip():
            next_item["conclusion"] = governing
            changed = True
        rewritten.append(next_item)

    if not changed:
        return determinations
    if determinations is None:
        return {"determinations": rewritten}
    return {**determinations, "determinations": rewritten}


def apply_field_context_overrides(
    ctx: SectionContext,
    field_context: dict[str, str] | None,
) -> SectionContext:
    """Return a copy of ``ctx`` with workbench field_context preferred over lake facts."""
    if not field_context:
        return ctx

    overrides = {code: value.strip() for code, value in field_context.items() if str(value).strip()}
    if not overrides:
        return ctx

    has_jurisdiction_override = any(code in overrides for code in _JURISDICTION_FE_CODES)
    if not has_jurisdiction_override and not any(code in overrides for code in _FE_TO_LAKE_FACT):
        return ctx

    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else None
    inner = _inner_facts(facts_payload)
    facts_changed = False
    for fe_code, lake_keys in _FE_TO_LAKE_FACT.items():
        value = overrides.get(fe_code)
        if not value:
            continue
        for lake_key in lake_keys:
            if inner.get(lake_key) != value:
                inner[lake_key] = value
                facts_changed = True
        # Also stamp FE codes into facts so descriptive renders see them directly.
        if inner.get(fe_code) != value:
            inner[fe_code] = value
            facts_changed = True

    for fe_code in _JURISDICTION_FE_CODES:
        value = overrides.get(fe_code)
        if value and inner.get(fe_code) != value:
            inner[fe_code] = value
            facts_changed = True

    related = dict(ctx.related_facts)
    related_changed = False
    if has_jurisdiction_override and "jurisdiction" in related:
        juris_section = related.get("jurisdiction")
        juris_inner = _inner_facts(juris_section if isinstance(juris_section, dict) else None)
        governing = overrides.get("GOVERNING_JURIS", "")
        if governing and juris_inner.get("jurisdiction_primary") != governing:
            juris_inner["jurisdiction_primary"] = governing
            related["jurisdiction"] = _with_inner_facts(
                juris_section if isinstance(juris_section, dict) else None,
                juris_inner,
            )
            related_changed = True

    determinations = ctx.determinations
    if has_jurisdiction_override:
        determinations = _rewrite_determinations(
            determinations,
            governing=overrides.get("GOVERNING_JURIS", ""),
            permitting=overrides.get("PERMITTING_AUTHORITY_DETAIL", ""),
        )

    if not facts_changed and not related_changed and determinations is ctx.determinations:
        return ctx

    return ctx.model_copy(
        update={
            "facts": _with_inner_facts(facts_payload, inner) if facts_changed else ctx.facts,
            "related_facts": related if related_changed else ctx.related_facts,
            "determinations": determinations,
        }
    )


def _field_context_allows_appraisal_fact(
    field_context: dict[str, str] | None, lake_key: str
) -> bool:
    if not field_context:
        return False
    for code in _PARCEL_APPRAISAL_FACT_ALLOW[lake_key]:
        raw = field_context.get(code)
        if raw is not None and str(raw).strip():
            return True
    return False


def redact_unprompted_parcel_appraisal_facts(
    ctx: SectionContext,
    field_context: dict[str, str] | None,
) -> SectionContext:
    """Omit CAD appraisal lake keys from parcel facts unless Prompt Lab allowed them.

    ``_compact(field_values)`` dumps the inner parcel-overview dict. Valuation and
    living-area columns are in that bag by default; drop them unless field_context
    includes the lake key or the FE compose code (CAD_VALUATION / BUILDING_DETAIL).
    """
    if ctx.section_id not in _PARCEL_SECTION_IDS:
        return ctx
    facts_payload = ctx.facts if isinstance(ctx.facts, dict) else None
    if not facts_payload:
        return ctx

    drop_keys = {
        key
        for key in _PARCEL_APPRAISAL_LAKE_KEYS
        if not _field_context_allows_appraisal_fact(field_context, key)
    }
    if not drop_keys:
        return ctx

    inner = _inner_facts(facts_payload)
    evidence = facts_payload.get("evidence")
    facts_changed = any(key in inner for key in drop_keys)
    evidence_changed = isinstance(evidence, dict) and any(key in evidence for key in drop_keys)
    if not facts_changed and not evidence_changed:
        return ctx

    new_inner = {key: value for key, value in inner.items() if key not in drop_keys}
    new_payload = _with_inner_facts(facts_payload, new_inner)
    if evidence_changed and isinstance(new_payload, dict) and isinstance(evidence, dict):
        new_payload = {
            **new_payload,
            "evidence": {key: value for key, value in evidence.items() if key not in drop_keys},
        }
    return ctx.model_copy(update={"facts": new_payload})
