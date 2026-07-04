"""Tests for the retrieval policy: two-ordering ranking + final-finding gating."""

from __future__ import annotations

from datetime import date

from civilai_agent.knowledge.ingestion_contracts import plan_ingestion
from civilai_agent.knowledge.retrieval_policy import (
    RETRIEVAL_PRIORITY,
    RetrievalQuery,
    can_support_final_finding,
    final_finding_candidates,
    rank_sources,
)
from civilai_agent.knowledge.source_models import (
    AuthorityLevel,
    Domain,
    ExpiryPolicy,
    KnowledgeSource,
    RefreshCadence,
    RetrievalIndex,
    SourceCategory,
)
from civilai_agent.knowledge.source_registry import SourceRegistry


def _source(
    source_id: str, category: SourceCategory, authority: AuthorityLevel, **kw: object
) -> KnowledgeSource:
    base: dict[str, object] = {
        "source_id": source_id,
        "name": source_id,
        "source_category": category,
        "authority_level": authority,
    }
    base.update(kw)
    return KnowledgeSource.model_validate(base)


def test_retrieval_priority_covers_all_categories() -> None:
    assert set(RETRIEVAL_PRIORITY) == set(SourceCategory)
    # Project records surface before regulatory (retrieval priority != authority).
    assert RETRIEVAL_PRIORITY.index(SourceCategory.PROJECT_RECORDS) < RETRIEVAL_PRIORITY.index(
        SourceCategory.REGULATORY_AUTHORITY
    )


def test_project_records_outrank_prior_reports_in_retrieval() -> None:
    registry = SourceRegistry(
        [
            _source(
                "prior",
                SourceCategory.PRIOR_REPORTS,
                AuthorityLevel.PRIOR_REPORT,
                applicable_domains=[Domain.ZONING],
            ),
            _source(
                "project",
                SourceCategory.PROJECT_RECORDS,
                AuthorityLevel.PROJECT_SPECIFIC,
                applicable_domains=[Domain.ZONING],
                can_support_final_finding=True,
            ),
        ]
    )
    ranked = rank_sources(registry, RetrievalQuery(domain=Domain.ZONING))
    assert [r.source.source_id for r in ranked] == ["project", "prior"]


def test_regulatory_outranks_prior_report_in_retrieval() -> None:
    registry = SourceRegistry(
        [
            _source("prior", SourceCategory.PRIOR_REPORTS, AuthorityLevel.PRIOR_REPORT),
            _source(
                "code",
                SourceCategory.REGULATORY_AUTHORITY,
                AuthorityLevel.REGULATORY,
                can_support_final_finding=True,
            ),
        ]
    )
    ranked = rank_sources(registry, RetrievalQuery(domain=Domain.ZONING))
    assert ranked[0].source.source_id == "code"
    assert ranked[-1].source.source_id == "prior"


def test_prior_report_and_blog_cannot_support_final_finding() -> None:
    prior = _source("prior", SourceCategory.PRIOR_REPORTS, AuthorityLevel.PRIOR_REPORT)
    blog = _source("blog", SourceCategory.SECONDARY_EXPLAINERS, AuthorityLevel.SECONDARY)
    assert not can_support_final_finding(prior)
    assert not can_support_final_finding(blog)


def test_regulatory_supports_final_when_current_and_applicable() -> None:
    code = _source(
        "code",
        SourceCategory.REGULATORY_AUTHORITY,
        AuthorityLevel.REGULATORY,
        applicable_counties=["travis"],
        refresh_cadence=RefreshCadence.ON_VERSION_CHANGE,
        last_checked_at=date(2026, 7, 1),
        can_support_final_finding=True,
    )
    assert can_support_final_finding(code, as_of=date(2026, 7, 4))


def test_stale_regulatory_cannot_support_final_finding() -> None:
    # A code we haven't re-verified past its window is not safe to cite as current.
    stale_code = _source(
        "stale_code",
        SourceCategory.REGULATORY_AUTHORITY,
        AuthorityLevel.REGULATORY,
        refresh_cadence=RefreshCadence.MONTHLY,
        last_checked_at=date(2026, 1, 1),
        can_support_final_finding=True,
    )
    assert not can_support_final_finding(stale_code, as_of=date(2026, 7, 4))


def test_project_utility_letter_supports_but_requires_human_review() -> None:
    letter = _source(
        "will_serve",
        SourceCategory.PROJECT_RECORDS,
        AuthorityLevel.PROJECT_SPECIFIC,
        applicable_domains=[Domain.UTILITIES],
        can_support_final_finding=True,
        requires_human_confirmation=True,
    )
    assert can_support_final_finding(letter)
    assert letter.requires_human_confirmation is True


def test_expired_alert_dropped_when_stale() -> None:
    registry = SourceRegistry(
        [
            _source(
                "agenda",
                SourceCategory.ALERTS,
                AuthorityLevel.ALERT,
                applicable_domains=[Domain.PERMITTING],
                refresh_cadence=RefreshCadence.WEEKLY,
                last_checked_at=date(2026, 1, 1),
                expiry_policy=ExpiryPolicy.EXPIRE_WHEN_STALE,
            ),
        ]
    )
    q = RetrievalQuery(domain=Domain.PERMITTING, as_of=date(2026, 7, 4))
    assert rank_sources(registry, q) == ()
    # ...but visible if we explicitly include stale.
    q2 = RetrievalQuery(domain=Domain.PERMITTING, as_of=date(2026, 7, 4), include_stale=True)
    assert len(rank_sources(registry, q2)) == 1


def test_jurisdiction_filter_in_ranking() -> None:
    registry = SourceRegistry(
        [
            _source(
                "travis_code",
                SourceCategory.REGULATORY_AUTHORITY,
                AuthorityLevel.REGULATORY,
                applicable_counties=["travis"],
                applicable_domains=[Domain.ZONING],
                can_support_final_finding=True,
            ),
        ]
    )
    hays_q = RetrievalQuery(domain=Domain.ZONING, county="hays")
    travis_q = RetrievalQuery(domain=Domain.ZONING, county="travis")
    assert rank_sources(registry, hays_q) == ()
    assert len(rank_sources(registry, travis_q)) == 1


def test_final_finding_candidates_filters_to_supportable() -> None:
    registry = SourceRegistry.from_seed()
    q = RetrievalQuery(
        domain=Domain.FLOODPLAIN, county="travis", city="austin", as_of=date(2026, 7, 4)
    )
    candidates = final_finding_candidates(registry, q)
    assert candidates, "expected at least one final-finding-capable floodplain source"
    assert all(c.can_support_final_finding for c in candidates)
    assert all(
        c.source.authority_level
        not in {AuthorityLevel.PRIOR_REPORT, AuthorityLevel.SECONDARY, AuthorityLevel.ALERT}
        for c in candidates
    )


def test_plan_ingestion_expands_indexes() -> None:
    src = _source(
        "multi",
        SourceCategory.REGULATORY_AUTHORITY,
        AuthorityLevel.REGULATORY,
        retrieval_indexes=[RetrievalIndex.REGULATORY_AUTHORITY, RetrievalIndex.AGENCY_GUIDANCE],
    )
    jobs = plan_ingestion([src])
    assert {(j.source_id, j.index) for j in jobs} == {
        ("multi", RetrievalIndex.REGULATORY_AUTHORITY),
        ("multi", RetrievalIndex.AGENCY_GUIDANCE),
    }
