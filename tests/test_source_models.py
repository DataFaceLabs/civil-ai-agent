"""Tests for the knowledge-layer models and their in-code safety enforcement."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from civilai_agent.knowledge.source_models import (
    AUTHORITY_RANK,
    AgentFinding,
    AuthorityLevel,
    Domain,
    EvidenceItem,
    KnowledgeSource,
    RefreshCadence,
    RetrievalIndex,
    SourceCategory,
)


def _source(**overrides: object) -> KnowledgeSource:
    base: dict[str, object] = {
        "source_id": "s1",
        "name": "Test Source",
        "source_category": SourceCategory.REGULATORY_AUTHORITY,
        "authority_level": AuthorityLevel.REGULATORY,
    }
    base.update(overrides)
    return KnowledgeSource.model_validate(base)


def test_authority_rank_orders_high_to_low() -> None:
    ranks = [AUTHORITY_RANK[level] for level in AuthorityLevel]
    assert ranks == sorted(ranks), "declaration order should mirror rank order"
    assert (
        AUTHORITY_RANK[AuthorityLevel.REGULATORY] < AUTHORITY_RANK[AuthorityLevel.PROJECT_SPECIFIC]
    )
    assert (
        AUTHORITY_RANK[AuthorityLevel.PROJECT_SPECIFIC]
        < AUTHORITY_RANK[AuthorityLevel.PRIOR_REPORT]
    )
    assert AUTHORITY_RANK[AuthorityLevel.SECONDARY] < AUTHORITY_RANK[AuthorityLevel.ALERT]


def test_retrieval_index_defaults_from_category() -> None:
    src = _source()
    assert src.retrieval_indexes == (RetrievalIndex.REGULATORY_AUTHORITY,)


def test_source_can_belong_to_multiple_indexes() -> None:
    src = _source(
        retrieval_indexes=[
            RetrievalIndex.REGULATORY_AUTHORITY,
            RetrievalIndex.AGENCY_GUIDANCE,
        ]
    )
    assert len(src.retrieval_indexes) == 2


@pytest.mark.parametrize(
    "authority",
    [AuthorityLevel.PRIOR_REPORT, AuthorityLevel.SECONDARY, AuthorityLevel.ALERT],
)
def test_non_final_authority_cannot_support_final_finding(authority: AuthorityLevel) -> None:
    with pytest.raises(ValidationError, match="never support a final"):
        _source(
            source_category=SourceCategory.PRIOR_REPORTS,
            authority_level=authority,
            can_support_final_finding=True,
        )


def test_regulatory_source_may_support_final_finding() -> None:
    src = _source(can_support_final_finding=True)
    assert src.can_support_final_finding is True


def test_jurisdiction_match_by_county_and_city() -> None:
    src = _source(applicable_counties=["Travis"], applicable_cities=["Austin"])
    assert src.applies_to_jurisdiction(county="travis")
    assert src.applies_to_jurisdiction(city="AUSTIN")  # normalized, case-insensitive
    assert not src.applies_to_jurisdiction(county="hays")


def test_geography_agnostic_source_applies_everywhere() -> None:
    src = _source()  # no counties/cities/etj -> national (e.g. FEMA NFIP)
    assert src.applies_to_jurisdiction(county="hays")
    assert src.applies_to_jurisdiction(city="anything")


def test_domain_match_empty_means_general() -> None:
    general = _source()
    scoped = _source(applicable_domains=[Domain.UTILITIES])
    assert general.applies_to_domain(Domain.ZONING)
    assert scoped.applies_to_domain(Domain.UTILITIES)
    assert not scoped.applies_to_domain(Domain.ZONING)


def test_staleness_scheduled_source() -> None:
    src = _source(refresh_cadence=RefreshCadence.WEEKLY, last_checked_at=date(2026, 6, 1))
    assert src.is_stale(date(2026, 7, 4))  # way past a week
    assert not src.is_stale(date(2026, 6, 5))  # within a week


def test_staleness_never_and_upload_are_never_stale() -> None:
    never = _source(refresh_cadence=RefreshCadence.NEVER, last_checked_at=None)
    upload = _source(
        source_category=SourceCategory.PROJECT_RECORDS,
        authority_level=AuthorityLevel.PROJECT_SPECIFIC,
        refresh_cadence=RefreshCadence.ON_UPLOAD,
    )
    assert not never.is_stale(date(2030, 1, 1))
    assert not upload.is_stale(date(2030, 1, 1))


def test_scheduled_source_never_checked_is_stale() -> None:
    src = _source(refresh_cadence=RefreshCadence.MONTHLY, last_checked_at=None)
    assert src.is_stale(date(2026, 7, 4))


def test_confidence_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        _source(confidence_default=1.5)


# -- evidence contract (AgentFinding) --------------------------------------------------


def _evidence(authority: AuthorityLevel, source_id: str = "e1") -> EvidenceItem:
    return EvidenceItem(source_id=source_id, authority_level=authority)


def test_finding_with_regulatory_controlling_source_ok() -> None:
    finding = AgentFinding(
        finding_text="The site is within Zone X.",
        domain=Domain.FLOODPLAIN,
        evidence_items=(_evidence(AuthorityLevel.OFFICIAL_RECORD, "firm"),),
        controlling_source="firm",
        authority_level=AuthorityLevel.OFFICIAL_RECORD,
        requires_human_review=False,
    )
    assert finding.controlling_source == "firm"


def test_finding_controlling_source_must_be_in_evidence() -> None:
    with pytest.raises(ValidationError, match="not among evidence_items"):
        AgentFinding(
            finding_text="x",
            domain=Domain.ZONING,
            evidence_items=(_evidence(AuthorityLevel.REGULATORY, "a"),),
            controlling_source="b",
        )


def test_finding_cannot_be_controlled_by_prior_report() -> None:
    with pytest.raises(ValidationError, match="cannot control a final finding"):
        AgentFinding(
            finding_text="Similar prior reports handled this by X.",
            domain=Domain.ZONING,
            evidence_items=(_evidence(AuthorityLevel.PRIOR_REPORT, "prior"),),
            controlling_source="prior",
            authority_level=AuthorityLevel.PRIOR_REPORT,
        )


def test_background_only_finding_forced_to_human_review() -> None:
    with pytest.raises(ValidationError, match="requires_human_review"):
        AgentFinding(
            finding_text="Some background context.",
            domain=Domain.DRAINAGE,
            evidence_items=(_evidence(AuthorityLevel.SECONDARY, "blog"),),
            requires_human_review=False,
        )


def test_background_only_finding_ok_when_flagged_for_review() -> None:
    finding = AgentFinding(
        finding_text="A blog suggests verifying the detention trigger.",
        domain=Domain.DRAINAGE,
        evidence_items=(_evidence(AuthorityLevel.SECONDARY, "blog"),),
        requires_human_review=True,
    )
    assert finding.controlling_source is None
    assert finding.requires_human_review is True
