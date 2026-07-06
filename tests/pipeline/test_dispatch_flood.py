"""Contract tests for flood branch dispatcher (S4.1)."""

from __future__ import annotations

from typing import Any

from civilai_agent.pipeline.dispatch.flood import dispatch_flood
from civilai_agent.pipeline.fetch import SectionContext


def _ctx(*, facts: dict[str, Any] | None = None) -> SectionContext:
    return SectionContext(
        entity_id="ent-flood",
        section_id="flood",
        facts=facts,
    )


def test_zone_x_branch_tier1() -> None:
    spec = dispatch_flood(
        _ctx(
            facts={
                "facts": {
                    "fema_zone": "X",
                    "floodway_flag": False,
                    "panel_id": None,
                    "effective_date": None,
                },
                "evidence": {
                    "fema_zone": [
                        {"source_record_id": "48453C_2244", "citation_url": "https://fema.gov"}
                    ]
                },
            }
        )
    )
    assert spec.branch_id == "flood.zone_x"
    assert spec.tier == 1
    assert spec.slots["flood_zone"] == "X"
    assert spec.slots["county_name"] == "Travis"
    assert any(m.name == "firm_panel_id" for m in spec.missing_inputs)


def test_sfha_branch_tier2() -> None:
    spec = dispatch_flood(
        _ctx(
            facts={
                "facts": {
                    "fema_zone": "AE",
                    "floodway_flag": False,
                    "panel_id": "48453C0495J",
                    "effective_date": "2014-08-18",
                }
            }
        )
    )
    assert spec.branch_id == "flood.sfha"
    assert spec.tier == 2
    assert spec.slots["panel_id"] == "48453C0495J"
    assert any(m.name == "proposed_work_scope" for m in spec.missing_inputs)
    assert any("regulatory floodway is not mapped" in stem.lower() for stem in spec.stems)


def test_null_zone_unknown_branch() -> None:
    spec = dispatch_flood(_ctx(facts={"facts": {"fema_zone": None}}))
    assert spec.branch_id == "flood.unknown"
    assert spec.tier == 2


def test_null_floodway_surfaces_gap() -> None:
    spec = dispatch_flood(_ctx(facts={"facts": {"fema_zone": "AE", "floodway_flag": None}}))
    assert any(m.name == "floodway_flag" for m in spec.missing_inputs)


def test_false_floodway_no_unknown_gap() -> None:
    spec = dispatch_flood(_ctx(facts={"facts": {"fema_zone": "X", "floodway_flag": False}}))
    assert not any(m.name == "floodway_flag" for m in spec.missing_inputs)
