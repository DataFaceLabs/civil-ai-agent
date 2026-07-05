"""Contract tests for zoning branch dispatcher (S3.1)."""

from __future__ import annotations

from typing import Any

import pytest

from civilai_agent.pipeline.dispatch.zoning import dispatch_zoning
from civilai_agent.pipeline.fetch import SectionContext


def _ctx(
    *,
    entity_id: str = "ent-1",
    facts: dict[str, Any] | None = None,
    determinations: dict[str, Any] | None = None,
) -> SectionContext:
    return SectionContext(
        entity_id=entity_id,
        section_id="zoning",
        facts=facts,
        determinations=determinations,
    )


def _zoning_det(**inputs: Any) -> dict[str, Any]:
    return {
        "determinations": [
            {
                "determination_id": "zoning_district",
                "inputs_used": inputs,
            }
        ]
    }


def test_pending_branch() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": None,
                    "allowed_use_flags": (
                        '["zoning_lookup_pending","manual_zoning_review_recommended"]'
                    ),
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "Travis County (municipality unresolved)",
                    "jurisdiction.review_track": "county_baseline",
                    "jurisdiction.in_etj": False,
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.pending"
    assert spec.tier == 2
    assert "manual review" in spec.stems[0].lower()


def test_county_no_zoning_branch() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={"facts": {"zoning_code": None, "allowed_use_flags": "[]"}},
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "Travis County",
                    "jurisdiction.review_track": "county_baseline",
                    "jurisdiction.in_etj": False,
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.county_no_zoning"
    assert spec.tier == 0
    assert "Travis County" in spec.stems[0]


def test_etj_branch() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={"facts": {"zoning_code": None, "allowed_use_flags": "[]"}},
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "City of Kyle (ETJ)",
                    "jurisdiction.in_etj": True,
                    "jurisdiction.review_track": "municipal_etj",
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.etj"
    assert spec.tier == 0
    assert "City of Kyle" in spec.stems[0]


def test_coa_limited_purpose_branch() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": "DR",
                    "zoning_base": "Development Reserve",
                    "allowed_use_flags": '["zoning_code_present"]',
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "City of Austin (limited purpose)",
                    "jurisdiction.review_track": "municipal_limited_purpose",
                    "jurisdiction.in_city_limits": False,
                    "jurisdiction.in_etj": False,
                    "zoning.zoning_code": "DR",
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.coa_limited_purpose"
    assert spec.tier == 2
    assert any("limited-purpose" in stem.lower() for stem in spec.stems)


def test_zoned_city_branch() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": "CS",
                    "zoning_base": "Commercial Services",
                    "allowed_use_flags": '["general_commercial"]',
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "City of Austin",
                    "jurisdiction.in_city_limits": True,
                    "jurisdiction.in_etj": False,
                    "zoning.zoning_code": "CS",
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.zoned_city"
    assert spec.tier == 2
    assert spec.missing_inputs[0].name == "proposed_use"


def test_counterfactual_limited_purpose_with_code_not_county() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": "DR",
                    "zoning_base": "Development Reserve",
                    "allowed_use_flags": "[]",
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "City of Austin (limited purpose)",
                    "jurisdiction.review_track": "municipal_limited_purpose",
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.coa_limited_purpose"
    assert spec.branch_id != "zoning.county_no_zoning"


def test_counterfactual_pending_not_county() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": None,
                    "allowed_use_flags": '["zoning_lookup_pending"]',
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "Travis County (municipality unresolved)",
                    "jurisdiction.review_track": "county_baseline",
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.pending"
    assert spec.branch_id != "zoning.county_no_zoning"


def test_counterfactual_county_jurisdiction_with_code_routes_zoned_city() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": "CS",
                    "zoning_base": "General Commercial Services",
                    "allowed_use_flags": "[]",
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "Travis County",
                    "jurisdiction.review_track": "county_baseline",
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.zoned_city"
    assert spec.branch_id != "zoning.county_no_zoning"


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (["zoning_lookup_pending"], "zoning.pending"),
        (["manual_zoning_review_recommended"], "zoning.pending"),
    ],
)
def test_pending_flag_variants(flags: list[str], expected: str) -> None:
    import json

    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": "MF-2",
                    "allowed_use_flags": json.dumps(flags),
                }
            }
        )
    )
    assert spec.branch_id == expected
