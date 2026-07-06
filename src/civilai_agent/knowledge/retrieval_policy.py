"""Retrieval policy: rank knowledge sources for a query, and gate final findings.

Two orderings, kept deliberately separate:

* **Retrieval priority** (:data:`RETRIEVAL_PRIORITY`) -- *what to surface first* for a
  parcel/project question. Project-specific records come first because, for a specific
  site, its own survey/title/letters are the most relevant evidence; then current adopted
  code; then official records; and so on down to alerts. This is category-derived.

* **Authority** (``KnowledgeSource.authority_rank``) -- *how much weight a source may
  carry and whether it can decide*. Regulatory outranks everything; precedent, background,
  and alerts can never decide. This is per-source and orthogonal to retrieval priority:
  a utility will-serve *letter* and a published service *policy* share a category but not
  an authority level.

The policy never lets a low-authority source become controlling evidence -- that rule is
also enforced structurally in :class:`~civilai_agent.knowledge.source_models.AgentFinding`,
so it holds even if a caller bypasses this policy.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from civilai_agent.knowledge.source_models import (
    NON_FINAL_AUTHORITY,
    Domain,
    ExpiryPolicy,
    KnowledgeSource,
    SourceCategory,
)
from civilai_agent.knowledge.source_registry import SourceRegistry

# Retrieval-priority tiers A..I from the design. Index in this tuple == tier (lower first).
RETRIEVAL_PRIORITY: tuple[SourceCategory, ...] = (
    SourceCategory.PROJECT_RECORDS,  # A: this parcel's own records
    SourceCategory.REGULATORY_AUTHORITY,  # B: current adopted code / manuals
    SourceCategory.PUBLIC_CASES,  # C: official + public records
    SourceCategory.AGENCY_GUIDANCE,  # D: agency checklists / guides
    SourceCategory.UTILITY_PROVIDER_RECORDS,  # E: utility / fire / agency correspondence
    SourceCategory.PRIOR_REPORTS,  # F: prior ATX Civil reports (precedent only)
    SourceCategory.ENVIRONMENTAL_TECHNICAL,  # G: technical references (explanation)
    SourceCategory.SECONDARY_EXPLAINERS,  # H: background only
    SourceCategory.ALERTS,  # I: flag possible changes only
)

_CATEGORY_TIER: dict[SourceCategory, int] = {
    category: tier for tier, category in enumerate(RETRIEVAL_PRIORITY)
}


class RetrievalQuery(BaseModel):
    """What the agent is looking for. Geography is optional (some domains are national)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    domain: Domain
    county: str | None = None
    city: str | None = None
    as_of: date | None = None
    include_stale: bool = False
    """When False (default), age-stale scheduled sources and expired alerts are dropped."""


class RankedSource(BaseModel):
    """A source paired with its computed ordering for a query."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: KnowledgeSource
    retrieval_tier: int
    authority_rank: int
    is_stale: bool
    can_support_final_finding: bool

    @property
    def sort_key(self) -> tuple[int, int, int, float]:
        # Retrieval tier first (what to surface), then authority, then fresh-before-stale,
        # then higher default confidence first (negated for ascending sort).
        return (
            self.retrieval_tier,
            self.authority_rank,
            int(self.is_stale),
            -self.source.confidence_default,
        )


def can_support_final_finding(source: KnowledgeSource, *, as_of: date | None = None) -> bool:
    """Whether a source may back a final feasibility finding *right now*.

    Requires all three: the per-source flag is set, the authority level is one that may
    decide (enforced at load, re-checked here as defense in depth), and -- for scheduled
    sources -- it isn't age-stale. A code you haven't re-verified past its refresh window
    is not safe to cite as current.
    """
    if not source.can_support_final_finding:
        return False
    if source.authority_level in NON_FINAL_AUTHORITY:
        return False
    return not (as_of is not None and source.is_stale(as_of))


def _is_dropped(source: KnowledgeSource, query: RetrievalQuery) -> bool:
    """Whether a source should be filtered out entirely for this query."""
    if query.include_stale or query.as_of is None:
        return False
    return source.expiry_policy == ExpiryPolicy.EXPIRE_WHEN_STALE and source.is_stale(query.as_of)


def rank_sources(registry: SourceRegistry, query: RetrievalQuery) -> tuple[RankedSource, ...]:
    """Return applicable sources ordered by retrieval priority then authority.

    Applicability = domain matches and jurisdiction matches. Expired alerts are dropped;
    age-stale sources are kept but marked (unless ``include_stale`` is False *and* they
    are set to expire), so the agent can still see a stale code exists while knowing not
    to treat it as final.
    """
    ranked: list[RankedSource] = []
    for source in registry.all():
        if not source.applies_to_domain(query.domain):
            continue
        if not source.applies_to_jurisdiction(county=query.county, city=query.city):
            continue
        if _is_dropped(source, query):
            continue
        stale = source.is_stale(query.as_of) if query.as_of is not None else False
        ranked.append(
            RankedSource(
                source=source,
                retrieval_tier=_CATEGORY_TIER[source.source_category],
                authority_rank=source.authority_rank,
                is_stale=stale,
                can_support_final_finding=can_support_final_finding(source, as_of=query.as_of),
            )
        )
    return tuple(sorted(ranked, key=lambda r: r.sort_key))


def final_finding_candidates(
    registry: SourceRegistry, query: RetrievalQuery
) -> tuple[RankedSource, ...]:
    """The subset of ranked sources that may actually back a final finding for this query."""
    return tuple(r for r in rank_sources(registry, query) if r.can_support_final_finding)
