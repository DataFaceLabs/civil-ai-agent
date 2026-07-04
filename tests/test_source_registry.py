"""Tests for the knowledge SourceRegistry: seed loading, indexing, staleness."""

from __future__ import annotations

from datetime import date

import pytest

from civilai_agent.knowledge.source_models import (
    AuthorityLevel,
    Domain,
    KnowledgeSource,
    RefreshCadence,
    RetrievalIndex,
    SourceCategory,
)
from civilai_agent.knowledge.source_registry import SourceRegistry


def _source(source_id: str, **overrides: object) -> KnowledgeSource:
    base: dict[str, object] = {
        "source_id": source_id,
        "name": source_id,
        "source_category": SourceCategory.REGULATORY_AUTHORITY,
        "authority_level": AuthorityLevel.REGULATORY,
    }
    base.update(overrides)
    return KnowledgeSource.model_validate(base)


def test_seed_registry_loads() -> None:
    registry = SourceRegistry.from_seed()
    assert len(registry) > 0
    # Every one of the nine categories is represented in the seed.
    present = {s.source_category for s in registry.all()}
    assert present == set(SourceCategory)


def test_seed_sources_have_required_metadata() -> None:
    registry = SourceRegistry.from_seed()
    for src in registry.all():
        assert src.source_id and src.name
        assert isinstance(src.source_category, SourceCategory)
        assert isinstance(src.authority_level, AuthorityLevel)
        assert src.retrieval_indexes  # always at least one (defaulted from category)
        assert 0.0 <= src.confidence_default <= 1.0


def test_seed_enforces_no_final_finding_for_low_authority() -> None:
    # Structural guarantee across the whole seed, not just unit-level.
    registry = SourceRegistry.from_seed()
    for src in registry.all():
        if src.authority_level in {
            AuthorityLevel.PRIOR_REPORT,
            AuthorityLevel.SECONDARY,
            AuthorityLevel.ALERT,
        }:
            assert not src.can_support_final_finding, src.source_id


def test_duplicate_source_id_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate source_id"):
        SourceRegistry([_source("dup"), _source("dup")])


def test_dangling_supersedes_rejected() -> None:
    with pytest.raises(ValueError, match="supersedes unknown"):
        SourceRegistry([_source("a", supersedes_source_id="ghost")])


def test_valid_supersedes_accepted() -> None:
    registry = SourceRegistry([_source("old"), _source("new", supersedes_source_id="old")])
    assert registry.superseded_ids() == frozenset({"old"})


def test_lookups_by_category_index_domain() -> None:
    registry = SourceRegistry(
        [
            _source("reg", applicable_domains=[Domain.ZONING]),
            _source(
                "guide",
                source_category=SourceCategory.AGENCY_GUIDANCE,
                authority_level=AuthorityLevel.AGENCY_GUIDANCE,
                applicable_domains=[Domain.PERMITTING],
            ),
        ]
    )
    assert {s.source_id for s in registry.by_category(SourceCategory.AGENCY_GUIDANCE)} == {"guide"}
    assert {s.source_id for s in registry.by_index(RetrievalIndex.REGULATORY_AUTHORITY)} == {"reg"}
    assert {s.source_id for s in registry.by_domain(Domain.ZONING)} == {"reg"}


def test_for_jurisdiction_filters() -> None:
    registry = SourceRegistry(
        [
            _source("travis_only", applicable_counties=["travis"]),
            _source("national"),  # no geography -> everywhere
        ]
    )
    hays = {s.source_id for s in registry.for_jurisdiction(county="hays")}
    assert hays == {"national"}
    travis = {s.source_id for s in registry.for_jurisdiction(county="travis")}
    assert travis == {"travis_only", "national"}


def test_stale_sources_detection() -> None:
    registry = SourceRegistry(
        [
            _source(
                "fresh", refresh_cadence=RefreshCadence.WEEKLY, last_checked_at=date(2026, 7, 3)
            ),
            _source("old", refresh_cadence=RefreshCadence.WEEKLY, last_checked_at=date(2026, 1, 1)),
            _source("immutable", refresh_cadence=RefreshCadence.NEVER),
        ]
    )
    stale = {s.source_id for s in registry.stale_sources(date(2026, 7, 4))}
    assert stale == {"old"}
