"""Shared quality-flag helpers for provenance-gated dispatch."""

from __future__ import annotations

from typing import Any

_CCN_OBSERVED: dict[str, str] = {
    "water": "water_ccn_overlay_observed",
    "wastewater": "wastewater_ccn_overlay_observed",
    "electric": "electric_ccn_overlay_observed",
}


def quality_flags(facts_payload: dict[str, Any] | None) -> frozenset[str]:
    if not isinstance(facts_payload, dict):
        return frozenset()
    quality = facts_payload.get("quality")
    if not isinstance(quality, dict):
        return frozenset()
    flags = quality.get("flags")
    if isinstance(flags, list):
        return frozenset(str(f).strip() for f in flags if f)
    return frozenset()


def ccn_provider_confirmed(facts_payload: dict[str, Any] | None, utility_kind: str) -> bool:
    """True when CCN spatial overlay (not baseline inference) selected the provider."""
    flag = _CCN_OBSERVED.get(utility_kind)
    if flag is None:
        return False
    return flag in quality_flags(facts_payload)
