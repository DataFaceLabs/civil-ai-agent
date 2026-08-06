"""Zoning scenario rails tools (ADR-0008).

These tools read the dual-rail zoning scenario from workbench context. They do not
invent ordinance citations — callers must only cite evidence returned here.
"""

from __future__ import annotations

import json
from typing import Any

from strands import tool

# Populated per-run by the runner / workflow from WorkbenchContext.zoning_scenario.
_ZONING_SCENARIO: dict[str, Any] | None = None


def set_zoning_scenario(scenario: dict[str, Any] | None) -> None:
    global _ZONING_SCENARIO
    _ZONING_SCENARIO = scenario


def get_zoning_scenario() -> dict[str, Any] | None:
    return _ZONING_SCENARIO


def _active_scenario(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None
    active_id = raw.get("active_scenario_id") or raw.get("activeScenarioId")
    scenarios = raw.get("scenarios") or []
    if not active_id or not isinstance(scenarios, list):
        return None
    for row in scenarios:
        if not isinstance(row, dict):
            continue
        sid = row.get("scenario_id") or row.get("scenarioId")
        if sid == active_id:
            return row
    return None


def _rail_fields(scenario: dict[str, Any], rail: str) -> dict[str, Any]:
    bundle = scenario.get(rail) or {}
    if not isinstance(bundle, dict):
        return {}
    fields = bundle.get("fields") or {}
    return fields if isinstance(fields, dict) else {}


def apply_analysis_basis_to_field_context(
    field_context: dict[str, str],
    zoning_scenario: dict[str, Any] | None,
) -> dict[str, str]:
    """When analysis_basis is proposed, overlay proposed zoning FE codes into field_context."""
    if not zoning_scenario:
        return field_context
    basis = zoning_scenario.get("analysis_basis") or zoning_scenario.get("analysisBasis")
    if basis != "proposed":
        return field_context
    active = _active_scenario(zoning_scenario)
    if not active:
        return field_context
    status = active.get("status")
    if status not in {"computed", "review", "accepted"}:
        return field_context
    proposed = _rail_fields(active, "proposed")
    out = dict(field_context)
    for code, raw in proposed.items():
        value = (
            str(raw.get("value") or "").strip()
            if isinstance(raw, dict)
            else str(raw).strip()
        )
        if value:
            out[str(code)] = value
    out["ZONING_ANALYSIS_BASIS"] = "proposed"
    out["ZONING_SCENARIO_LABEL"] = str(active.get("label") or "")
    return out


@tool
def get_zoning_rails() -> str:
    """Return baseline and proposed zoning fact rails for the active Zoning Change scenario.

    Cite only values and evidence returned by this tool. If no scenario exists, say so.
    """
    raw = get_zoning_scenario()
    if not raw:
        return json.dumps(
            {
                "status": "ok",
                "has_scenario": False,
                "message": "No zoning_scenario on this project.",
            }
        )
    active = _active_scenario(raw)
    basis = raw.get("analysis_basis") or raw.get("analysisBasis") or "baseline"
    payload = {
        "status": "ok",
        "has_scenario": active is not None,
        "analysis_basis": basis,
        "baseline_jurisdiction_key": raw.get("baseline_jurisdiction_key")
        or raw.get("baselineJurisdictionKey"),
        "effective_jurisdiction_key": raw.get("effective_jurisdiction_key")
        or raw.get("effectiveJurisdictionKey"),
        "active_scenario": active,
    }
    return json.dumps(payload, default=str)


@tool
def get_zoning_comparisons() -> str:
    """Return per-fact baseline vs proposed diffs, risks, and ordinance evidence.

    Never invent section numbers or citations — use only evidence arrays returned here.
    """
    raw = get_zoning_scenario()
    active = _active_scenario(raw)
    if not active:
        return json.dumps(
            {
                "status": "ok",
                "comparisons": [],
                "message": "No active zoning scenario comparisons.",
            }
        )
    return json.dumps(
        {
            "status": "ok",
            "scenario_id": active.get("scenario_id") or active.get("scenarioId"),
            "label": active.get("label"),
            "status_value": active.get("status"),
            "risk_summary": active.get("risk_summary") or active.get("riskSummary"),
            "comparisons": active.get("comparisons") or [],
        },
        default=str,
    )
