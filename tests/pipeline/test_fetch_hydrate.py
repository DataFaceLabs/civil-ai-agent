"""Tests for ordinance hydrate merge on zoning fetch."""

from __future__ import annotations

from unittest.mock import MagicMock

from civilai_agent.pipeline.fetch import (
    SectionContext,
    false_ic_gap_warning,
    jurisdiction_key_from_text,
    merge_impervious_hydrate,
    zoning_code_from_text,
)


def test_jurisdiction_and_zoning_parse() -> None:
    assert jurisdiction_key_from_text("City of Georgetown, Williamson County") == "georgetown"
    assert zoning_code_from_text("MF-1 — Low Density Multifamily") == "MF-1"


def test_merge_impervious_hydrate_stamps_regs() -> None:
    client = MagicMock()
    client.hydrate_regtext.return_value = {
        "families": {
            "impervious": {
                "status": "complete",
                "limit_pct": 50,
                "regs_text": "MF-1: 50% maximum impervious cover (Table 11.02.010.B).",
            }
        }
    }
    ctx = SectionContext(
        entity_id="e1",
        section_id="zoning",
        facts={"facts": {"jurisdiction_primary": "City of Georgetown", "zoning_code": "MF-1"}},
    )
    out = merge_impervious_hydrate(client, ctx, None)
    inner = out.facts["facts"] if isinstance(out.facts, dict) else {}
    assert inner["IMPERVIOUS_REGS"].startswith("MF-1: 50%")
    assert inner["IMPERVIOUS_COVER_LIMIT"] == "50%"
    assert inner["impervious_regs"].startswith("MF-1")
    assert out.hydrate_impervious_status == "complete"
    client.hydrate_regtext.assert_called_once_with("georgetown", "MF-1", ["impervious"])


def test_merge_skips_non_zoning() -> None:
    client = MagicMock()
    ctx = SectionContext(entity_id="e1", section_id="parcel", facts={"facts": {}})
    out = merge_impervious_hydrate(client, ctx, {"GOVERNING_JURIS": "Georgetown"})
    client.hydrate_regtext.assert_not_called()
    assert out is ctx


def test_false_ic_gap_warning() -> None:
    draft = "No tiered impervious cover table by land use or watershed tier is available in current records."
    assert false_ic_gap_warning(draft, "complete")
    assert false_ic_gap_warning("MF-1 is 50% IC.", "complete") is None
    assert false_ic_gap_warning(draft, None) is None
