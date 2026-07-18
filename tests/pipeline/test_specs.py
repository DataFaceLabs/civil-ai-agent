"""Tests for pipeline draft-spec contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from civilai_agent.pipeline.specs import DraftSpec, MissingInput


def test_draft_spec_round_trip() -> None:
    spec = DraftSpec(
        entity_id="ent-1",
        section_id="zoning",
        branch_id="zoning.coa_limited_purpose",
        tier=2,
        slots={"zoning_code": "DR", "jurisdiction_primary": "City of Austin limited purpose"},
        facts={"entity_id": "ent-1", "facts": {"zoning_code": "DR"}},
        determinations=[{"determination_id": "zoning_applies", "conclusion": "yes"}],
        citations=[{"source": "lake", "field": "zoning_code"}],
        stems=["Lead with the zoning designation."],
        missing_inputs=[
            MissingInput(
                name="proposed_use",
                why_needed="Rezoning verdict requires client's intended use.",
                resolution="client",
            )
        ],
        searchable_gaps=[],
    )
    restored = DraftSpec.model_validate(spec.model_dump())
    assert restored.branch_id == "zoning.coa_limited_purpose"
    assert restored.tier == 2
    assert restored.missing_inputs[0].resolution == "client"


@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_draft_spec_accepts_valid_tiers(tier: int) -> None:
    spec = DraftSpec(
        entity_id="e",
        section_id="flood",
        branch_id="flood.zone_x",
        tier=tier,
    )
    assert spec.tier == tier


@pytest.mark.parametrize("tier", [-1, 4, 99])
def test_draft_spec_rejects_invalid_tier(tier: int) -> None:
    with pytest.raises(ValidationError):
        DraftSpec(
            entity_id="e",
            section_id="zoning",
            branch_id="zoning.county_no_zoning",
            tier=tier,
        )
