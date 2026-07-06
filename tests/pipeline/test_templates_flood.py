"""Tier-1 flood template tests (S4.1)."""

from __future__ import annotations

from civilai_agent.pipeline.dispatch.flood import dispatch_flood
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.templates.flood import render_flood_tier1


def test_zone_x_master_stem_without_invented_panel() -> None:
    spec = dispatch_flood(
        SectionContext(
            entity_id="ent-1",
            section_id="flood",
            facts={
                "facts": {
                    "fema_zone": "X",
                    "floodway_flag": False,
                    "panel_id": None,
                    "effective_date": None,
                },
                "evidence": {
                    "fema_zone": [{"source_record_id": "48453C_2244"}],
                },
            },
        )
    )
    output = render_flood_tier1(spec)
    text = output.suggested_language.lower()
    assert "zone x" in text
    assert "travis county" in text
    assert "48453c" not in text
    assert "could not be confirmed from governed data" in text
    assert "regulatory floodway is not mapped" in text
