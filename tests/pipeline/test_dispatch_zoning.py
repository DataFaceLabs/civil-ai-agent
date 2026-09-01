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


def test_pending_branch_municipality_unresolved() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": None,
                    "allowed_use_flags": (
                        '["zoning_lookup_pending","manual_zoning_review_recommended"]'
                    ),
                    "impervious_regs": "Impervious cover limits are governed by COA Land Development Code",
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "Bastrop County (municipality unresolved)",
                    "jurisdiction.review_track": "county_baseline",
                    "jurisdiction.in_etj": False,
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.municipality_pending"
    assert spec.tier == 2
    assert "Bastrop" in spec.stems[0]
    assert spec.slots.get("impervious_regs") is None


def test_municipality_unresolved_strips_coa_bootstrap() -> None:
    """Maha Loop class: unresolved fringe city must not inherit COA LDC bootstrap prose."""
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": None,
                    "allowed_use_flags": (
                        '["zoning_lookup_pending","manual_zoning_review_recommended"]'
                    ),
                    "impervious_regs": (
                        "Impervious cover limits are governed by COA Land Development Code"
                    ),
                    "compatibility_stds": (
                        "Compatibility standards governed by COA Land Development Code Subchapter C"
                    ),
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": (
                        "Travis County (municipality unresolved)"
                    ),
                    "jurisdiction.review_track": "county_baseline",
                    "jurisdiction.in_etj": False,
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.municipality_pending"
    assert spec.slots.get("impervious_regs") is None
    assert spec.slots.get("compatibility_stds") is None
    assert any("Do not cite City of Austin" in stem for stem in spec.stems)


def test_pending_branch_without_municipality_unresolved() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": None,
                    "allowed_use_flags": '["zoning_lookup_pending"]',
                }
            },
        )
    )
    assert spec.branch_id == "zoning.pending"
    assert spec.tier == 2
    assert "manual review" in spec.stems[0].lower()


def test_county_null_zoning_pending_not_non_zoning_assertion() -> None:
    """H3: null zoning_code on county track must not assert non-zoning (Maha Loop class)."""
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
    assert spec.branch_id == "zoning.pending"
    assert spec.tier == 2
    assert "Do not assert" in spec.stems[1]


def test_county_no_zoning_branch_when_explicitly_confirmed() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": None,
                    "allowed_use_flags": '["county_non_zoning_confirmed"]',
                }
            },
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


def test_zoned_city_flags_missing_overlays_gap() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": "CS",
                    "zoning_base": "Commercial Services",
                    "overlays": "[]",
                    "allowed_use_flags": '["general_commercial"]',
                }
            },
            determinations=_zoning_det(
                **{
                    "jurisdiction.jurisdiction_primary": "City of Austin",
                    "jurisdiction.in_city_limits": True,
                    "zoning.zoning_code": "CS",
                }
            ),
        )
    )
    assert spec.branch_id == "zoning.zoned_city"
    assert any(m.name == "zoning_overlays" for m in spec.missing_inputs)
    assert any("Do not state that no overlays apply" in stem for stem in spec.stems)


def test_zoned_city_with_overlays_skips_overlay_gap() -> None:
    spec = dispatch_zoning(
        _ctx(
            facts={
                "facts": {
                    "zoning_code": "CS",
                    "overlays": '["MU","V","NP"]',
                    "allowed_use_flags": '["general_commercial"]',
                }
            },
            determinations=_zoning_det(**{"jurisdiction.jurisdiction_primary": "City of Austin"}),
        )
    )
    assert not any(m.name == "zoning_overlays" for m in spec.missing_inputs)


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
    assert spec.branch_id == "zoning.municipality_pending"
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


# --- typed use-absence reaches the writer (civil-ai-data#669 / #670) --------


def _seattle_ctx(density_limits: str | None) -> SectionContext:
    """A zoned city parcel whose jurisdiction has no rule pack.

    1600 9th Ave, Seattle: the case that shipped the internal sentinel
    "Non Texas Zoning Bootstrap Barred" to a customer.
    """
    facts: dict[str, Any] = {
        "facts": {
            "zoning_code": "DMC 340/290-440",
            "zoning_base": "Downtown Mixed Commercial 340/290-440",
            "allowed_use_flags": "[]",
            "overlays": "[]",
        }
    }
    if density_limits is not None:
        facts["facts"]["density_limits"] = density_limits
    return _ctx(
        facts=facts,
        determinations=_zoning_det(
            **{
                "jurisdiction.jurisdiction_primary": "City of Seattle",
                "jurisdiction.in_city_limits": True,
                "jurisdiction.in_etj": False,
            }
        ),
    )


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("no_pack_for_authority", "have not been onboarded"),
        ("code_unrecognised", "not among\nthose held"),
        ("uses_not_recorded", "has not been extracted"),
    ],
)
def test_each_absence_reason_reaches_the_stems(reason: str, expected: str) -> None:
    """Each names a different piece of work, so each must read differently."""
    spec = dispatch_zoning(_seattle_ctx(f'{{"absence_reason":"{reason}"}}'))
    joined = " ".join(spec.stems).replace("\n", " ")
    assert expected.replace("\n", " ") in joined


def test_absence_is_registered_as_a_tracked_gap() -> None:
    """A known coverage gap must be countable, not just narrated."""
    spec = dispatch_zoning(_seattle_ctx('{"absence_reason":"no_pack_for_authority"}'))
    names = [m.name for m in spec.missing_inputs]
    assert "zoning_uses:no_pack_for_authority" in names
    gap = next(m for m in spec.missing_inputs if m.name.startswith("zoning_uses:"))
    assert gap.resolution == "data-gap"


def test_no_absence_stem_when_uses_are_derived() -> None:
    """A district we can answer for must not carry an apology."""
    spec = dispatch_zoning(_seattle_ctx('{"development_pattern":"single_family_residential"}'))
    assert not any(m.name.startswith("zoning_uses:") for m in spec.missing_inputs)
    assert not any("onboarded" in stem for stem in spec.stems)


def test_unparseable_or_absent_density_limits_is_not_a_gap() -> None:
    """Older artifacts predate absence_reason; they must not grow a false gap."""
    for payload in (None, "not json", '{"constraint_source":"inferred"}'):
        spec = dispatch_zoning(_seattle_ctx(payload))
        assert not any(m.name.startswith("zoning_uses:") for m in spec.missing_inputs)


def test_the_retired_sentinel_is_not_a_recognised_reason() -> None:
    """non_texas_zoning_bootstrap_barred must never round-trip into prose again."""
    spec = dispatch_zoning(_seattle_ctx('{"absence_reason":"non_texas_zoning_bootstrap_barred"}'))
    assert not any("bootstrap" in stem.lower() for stem in spec.stems)
    assert not any(m.name.startswith("zoning_uses:") for m in spec.missing_inputs)
