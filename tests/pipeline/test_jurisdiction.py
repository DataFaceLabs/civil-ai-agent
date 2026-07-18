"""Tests for jurisdiction playbook routing."""

from __future__ import annotations

from civilai_agent.pipeline.dispatch.environmental import dispatch_environmental
from civilai_agent.pipeline.dispatch.flood import dispatch_flood
from civilai_agent.pipeline.fetch import SectionContext
from civilai_agent.pipeline.jurisdiction import (
    jurisdiction_context,
    requires_local_municipal_playbook,
)


def test_elgin_requires_local_municipal_playbook() -> None:
    ctx = SectionContext(
        entity_id="ent-elgin",
        section_id="environmental",
        related_facts={
            "jurisdiction": {
                "facts": {
                    "jurisdiction_primary": "Elgin city",
                    "in_city_limits": True,
                }
            }
        },
        determinations={
            "determinations": [
                {
                    "determination_id": "jurisdiction",
                    "inputs_used": {
                        "jurisdiction.jurisdiction_primary": "Elgin city",
                        "jurisdiction.in_city_limits": True,
                    },
                }
            ]
        },
    )
    jctx = jurisdiction_context(ctx)
    assert requires_local_municipal_playbook(jctx) is True


def test_environmental_elgin_routes_jurisdiction_pending() -> None:
    spec = dispatch_environmental(
        SectionContext(
            entity_id="ent-elgin",
            section_id="environmental",
            facts={"facts": {"wpap_type": "outside", "zone_type": "outside"}},
            related_facts={
                "jurisdiction": {
                    "facts": {
                        "jurisdiction_primary": "Elgin city",
                        "in_city_limits": True,
                    }
                }
            },
            determinations={
                "determinations": [
                    {
                        "determination_id": "jurisdiction",
                        "inputs_used": {
                            "jurisdiction.jurisdiction_primary": "Elgin city",
                            "jurisdiction.in_city_limits": True,
                        },
                    }
                ]
            },
        )
    )
    assert spec.branch_id == "environmental.jurisdiction_pending"
    assert any("Do NOT apply Travis County" in stem for stem in spec.stems)


def test_flood_elgin_routes_jurisdiction_pending() -> None:
    spec = dispatch_flood(
        SectionContext(
            entity_id="ent-elgin",
            section_id="flood",
            facts={"facts": {"fema_zone": "X", "panel_id": "48453C0470K"}},
            related_facts={
                "jurisdiction": {
                    "facts": {
                        "jurisdiction_primary": "Elgin city",
                        "in_city_limits": True,
                    }
                }
            },
            determinations={
                "determinations": [
                    {
                        "determination_id": "jurisdiction",
                        "inputs_used": {
                            "jurisdiction.jurisdiction_primary": "Elgin city",
                            "jurisdiction.in_city_limits": True,
                        },
                    }
                ]
            },
        )
    )
    assert spec.branch_id == "flood.jurisdiction_pending"
    assert any("Do NOT treat FEMA Zone X" in stem for stem in spec.stems)
