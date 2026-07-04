"""Typed models for the agent's unstructured/semi-structured knowledge layer.

This module defines *what a knowledge source is* and *what an evidence-backed finding
is* -- the data contracts only. It deliberately holds no ingestion, retrieval, or I/O
logic (see ``source_registry``, ``retrieval_policy``, ``ingestion_contracts``).

The load-bearing safety property lives here, enforced in code rather than prompt wording
(per this repo's stated principle): a source whose authority level is precedent-only,
explanatory, or an alert can **never** be marked as able to support a final feasibility
finding, and an :class:`AgentFinding` can **never** be constructed with a controlling
source of that kind. Bad configuration fails to load; unsafe findings fail to build.
"""

from __future__ import annotations

from datetime import date
from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AuthorityLevel(StrEnum):
    """How much weight a source may carry, from highest to lowest authority.

    ``rank`` (see :data:`AUTHORITY_RANK`) is what sorts these; the enum's declaration
    order is documentation only. Authority is about *can this support a final finding
    and how heavily*, which is distinct from *retrieval priority* (what to surface first
    for a parcel query) -- see ``retrieval_policy``.
    """

    REGULATORY = "regulatory"
    """Adopted code, criteria manual, ordinance, statute, official technical manual."""
    OFFICIAL_RECORD = "official_record"
    """Public/permit record, plat, deed, FEMA/FIS, agency record of fact."""
    AGENCY_GUIDANCE = "agency_guidance"
    """Checklist, guide, FAQ, permit packet, official agency webpage."""
    PROJECT_SPECIFIC = "project_specific"
    """Survey, title, utility letter, reviewer email, pre-app notes for this project."""
    PRIOR_REPORT = "prior_report"
    """A previous ATX Civil report or exhibit -- precedent/drafting only, never authority."""
    TECHNICAL_REFERENCE = "technical_reference"
    """NOAA/FEMA/USACE/NRCS/EPA/ASCE technical reference -- explanation, not controlling."""
    SECONDARY = "secondary"
    """Blog, article, explainer -- background only."""
    ALERT = "alert"
    """Agenda, public notice, official agency social update -- a pointer to verify, not fact."""


# Lower rank == higher authority. Used for sorting and for the final-finding gate.
AUTHORITY_RANK: dict[AuthorityLevel, int] = {
    AuthorityLevel.REGULATORY: 0,
    AuthorityLevel.OFFICIAL_RECORD: 1,
    AuthorityLevel.AGENCY_GUIDANCE: 2,
    AuthorityLevel.PROJECT_SPECIFIC: 3,
    AuthorityLevel.PRIOR_REPORT: 4,
    AuthorityLevel.TECHNICAL_REFERENCE: 5,
    AuthorityLevel.SECONDARY: 6,
    AuthorityLevel.ALERT: 7,
}

# Authority levels that may *never* back a final feasibility finding on their own,
# regardless of any per-source flag. This is the whole point of the layer: precedent,
# explanation, and alerts inform drafting but do not decide.
NON_FINAL_AUTHORITY: frozenset[AuthorityLevel] = frozenset(
    {AuthorityLevel.PRIOR_REPORT, AuthorityLevel.SECONDARY, AuthorityLevel.ALERT}
)


class SourceCategory(StrEnum):
    """The bucket a source belongs to. Drives its default retrieval index and its
    retrieval-priority tier (see ``retrieval_policy.RETRIEVAL_PRIORITY``)."""

    REGULATORY_AUTHORITY = "regulatory_authority"
    AGENCY_GUIDANCE = "agency_guidance"
    PROJECT_RECORDS = "project_records"
    PRIOR_REPORTS = "prior_reports"
    PUBLIC_CASES = "public_cases"
    UTILITY_PROVIDER_RECORDS = "utility_provider_records"
    ENVIRONMENTAL_TECHNICAL = "environmental_technical"
    SECONDARY_EXPLAINERS = "secondary_explainers"
    ALERTS = "alerts"


class RetrievalIndex(StrEnum):
    """A retrieval namespace / vector-store partition. Kept 1:1 with categories so we
    never mix an adopted ordinance and a blog into one undifferentiated store, but a
    source may be assigned to more than one index when it legitimately serves two."""

    REGULATORY_AUTHORITY = "regulatory_authority"
    AGENCY_GUIDANCE = "agency_guidance"
    PROJECT_RECORDS = "project_records"
    PRIOR_REPORTS = "prior_reports"
    PUBLIC_CASES = "public_cases"
    UTILITY_PROVIDER_RECORDS = "utility_provider_records"
    ENVIRONMENTAL_TECHNICAL = "environmental_technical"
    SECONDARY_EXPLAINERS = "secondary_explainers"
    ALERTS = "alerts"


# The canonical index for each category (used when a source doesn't override).
CATEGORY_DEFAULT_INDEX: dict[SourceCategory, RetrievalIndex] = {
    SourceCategory.REGULATORY_AUTHORITY: RetrievalIndex.REGULATORY_AUTHORITY,
    SourceCategory.AGENCY_GUIDANCE: RetrievalIndex.AGENCY_GUIDANCE,
    SourceCategory.PROJECT_RECORDS: RetrievalIndex.PROJECT_RECORDS,
    SourceCategory.PRIOR_REPORTS: RetrievalIndex.PRIOR_REPORTS,
    SourceCategory.PUBLIC_CASES: RetrievalIndex.PUBLIC_CASES,
    SourceCategory.UTILITY_PROVIDER_RECORDS: RetrievalIndex.UTILITY_PROVIDER_RECORDS,
    SourceCategory.ENVIRONMENTAL_TECHNICAL: RetrievalIndex.ENVIRONMENTAL_TECHNICAL,
    SourceCategory.SECONDARY_EXPLAINERS: RetrievalIndex.SECONDARY_EXPLAINERS,
    SourceCategory.ALERTS: RetrievalIndex.ALERTS,
}


class Domain(StrEnum):
    """Feasibility-study domains a source can inform. Aligned with the report sections
    the determination engine and agent already speak in."""

    PARCEL_JURISDICTION = "parcel_jurisdiction"
    ZONING = "zoning"
    PLATTING = "platting"
    WATERSHED = "watershed"
    IMPERVIOUS_COVER = "impervious_cover"
    FLOODPLAIN = "floodplain"
    DRAINAGE = "drainage"
    WATER_QUALITY = "water_quality"
    UTILITIES = "utilities"
    TRANSPORTATION = "transportation"
    FIRE_PROTECTION = "fire_protection"
    ENVIRONMENTAL_CONSTRAINTS = "environmental_constraints"
    EASEMENTS_SETBACKS = "easements_setbacks"
    PERMITTING = "permitting"
    RECOMMENDATIONS = "recommendations"


class RefreshCadence(StrEnum):
    """How a source stays current. Drives staleness detection in the registry."""

    NEVER = "never"
    """Immutable snapshot (a project upload, a prior report). Track dates, don't refresh."""
    ON_UPLOAD = "on_upload"
    """Project files: no scheduled refresh, but the upload/document date is tracked."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ON_VERSION_CHANGE = "on_version_change"
    """Codes/manuals: refresh when a new adopted version is published."""


# Approximate max age before a scheduled source is considered stale. ON_VERSION_CHANGE
# is treated like MONTHLY for the recheck heartbeat (we still poll for a new version);
# NEVER / ON_UPLOAD are never stale by age.
REFRESH_MAX_AGE_DAYS: dict[RefreshCadence, int | None] = {
    RefreshCadence.NEVER: None,
    RefreshCadence.ON_UPLOAD: None,
    RefreshCadence.WEEKLY: 7,
    RefreshCadence.MONTHLY: 31,
    RefreshCadence.QUARTERLY: 92,
    RefreshCadence.ON_VERSION_CHANGE: 31,
}


class FileFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    XML = "xml"
    JSON = "json"
    GEOJSON = "geojson"
    CSV = "csv"
    IMAGE = "image"
    TEXT = "text"
    OTHER = "other"


class ExpiryPolicy(IntEnum):
    """Whether stale alerts should be dropped from retrieval. Alerts expire; adopted
    actions they point to do not."""

    KEEP = 0
    EXPIRE_WHEN_STALE = 1


def _normalize_tokens(values: tuple[str, ...]) -> tuple[str, ...]:
    """Lowercase + strip jurisdiction/geography tokens for case-insensitive matching."""
    seen: list[str] = []
    for value in values:
        token = " ".join(value.strip().lower().split())
        if token and token not in seen:
            seen.append(token)
    return tuple(seen)


class KnowledgeSource(BaseModel):
    """One unstructured/semi-structured source the agent may retrieve from.

    Immutable once loaded (``frozen=True``); the registry owns the collection. Geography
    tokens (counties/cities/ETJ) are normalized to lowercase for matching.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""

    source_category: SourceCategory
    authority_level: AuthorityLevel

    jurisdiction: str | None = None
    geography: str | None = None
    applicable_counties: tuple[str, ...] = ()
    applicable_cities: tuple[str, ...] = ()
    applicable_etj: tuple[str, ...] = ()
    applicable_domains: tuple[Domain, ...] = ()

    retrieval_indexes: tuple[RetrievalIndex, ...] = ()

    source_owner: str | None = None
    publisher: str | None = None
    url: str | None = None
    local_path: str | None = None
    document_type: str | None = None
    file_format: FileFormat | None = None

    effective_date: date | None = None
    last_checked_at: date | None = None
    refresh_cadence: RefreshCadence = RefreshCadence.NEVER
    version: str | None = None
    supersedes_source_id: str | None = None

    confidence_default: float = Field(default=0.5, ge=0.0, le=1.0)
    citation_required: bool = True
    can_support_final_finding: bool = False
    requires_human_confirmation: bool = True
    expiry_policy: ExpiryPolicy = ExpiryPolicy.KEEP
    notes: str | None = None

    _norm_counties = field_validator("applicable_counties")(_normalize_tokens)
    _norm_cities = field_validator("applicable_cities")(_normalize_tokens)
    _norm_etj = field_validator("applicable_etj")(_normalize_tokens)

    @model_validator(mode="after")
    def _apply_defaults_and_safety(self) -> KnowledgeSource:
        # Default the retrieval index from the category when not explicitly assigned.
        if not self.retrieval_indexes:
            object.__setattr__(
                self, "retrieval_indexes", (CATEGORY_DEFAULT_INDEX[self.source_category],)
            )
        # THE safety gate: precedent/explanatory/alert authority can never be marked as
        # able to support a final finding. Fail the load rather than trust prose to hold
        # the line at answer time.
        if self.can_support_final_finding and self.authority_level in NON_FINAL_AUTHORITY:
            raise ValueError(
                f"source {self.source_id!r} has authority {self.authority_level} which can "
                "never support a final feasibility finding; set can_support_final_finding=false"
            )
        return self

    @property
    def authority_rank(self) -> int:
        return AUTHORITY_RANK[self.authority_level]

    def applies_to_domain(self, domain: Domain) -> bool:
        # An empty domain list means the source is general-purpose within its geography.
        return not self.applicable_domains or domain in self.applicable_domains

    def applies_to_jurisdiction(
        self, *, county: str | None = None, city: str | None = None
    ) -> bool:
        """True when the source covers the given county/city (or is geography-agnostic).

        A source with no geography tokens is treated as applying everywhere (e.g. FEMA
        NFIP guidance, NOAA Atlas 14). A source scoped to counties/cities applies only
        when the query's county or city matches one of them.
        """
        scoped = self.applicable_counties or self.applicable_cities or self.applicable_etj
        if not scoped:
            return True
        county_norm = " ".join(county.strip().lower().split()) if county else None
        city_norm = " ".join(city.strip().lower().split()) if city else None
        if county_norm and county_norm in self.applicable_counties:
            return True
        if city_norm and (city_norm in self.applicable_cities or city_norm in self.applicable_etj):
            return True
        return False

    def is_stale(self, as_of: date) -> bool:
        """True when a scheduled source is past its refresh window.

        Never-refreshed and upload-only sources are never stale by age. A scheduled
        source with no ``last_checked_at`` is considered stale (we've never verified it).
        """
        max_age = REFRESH_MAX_AGE_DAYS[self.refresh_cadence]
        if max_age is None:
            return False
        if self.last_checked_at is None:
            return True
        return (as_of - self.last_checked_at).days > max_age


class EvidenceItem(BaseModel):
    """A single piece of retrieved evidence backing a finding, pinned to its source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    authority_level: AuthorityLevel
    excerpt: str | None = None
    locator: str | None = None
    """Where in the source (page, section, table, exhibit)."""
    url: str | None = None
    retrieved_at: date | None = None

    @property
    def can_be_controlling(self) -> bool:
        """Whether this evidence may be the controlling source of a final finding."""
        return self.authority_level not in NON_FINAL_AUTHORITY


class AgentFinding(BaseModel):
    """An evidence-backed finding the agent produces. The evidence contract.

    Enforces in code that a finding is never *silently* backed only by precedent or
    background: if no evidence item can be controlling, the finding must carry no
    controlling source and must be flagged for human review.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_text: str = Field(min_length=1)
    domain: Domain
    parcel_id: str | None = None
    project_id: str | None = None

    evidence_items: tuple[EvidenceItem, ...] = ()
    controlling_source: str | None = None
    authority_level: AuthorityLevel | None = None

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    assumptions: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    requires_human_review: bool = True
    recommended_next_action: str | None = None

    @model_validator(mode="after")
    def _enforce_evidence_contract(self) -> AgentFinding:
        controllable = [e for e in self.evidence_items if e.can_be_controlling]
        if self.controlling_source is not None:
            match = next(
                (e for e in self.evidence_items if e.source_id == self.controlling_source), None
            )
            if match is None:
                raise ValueError(
                    f"controlling_source {self.controlling_source!r} is not among evidence_items"
                )
            if not match.can_be_controlling:
                raise ValueError(
                    f"controlling_source {self.controlling_source!r} has authority "
                    f"{match.authority_level} and cannot control a final finding"
                )
            if self.authority_level is not None and self.authority_level != match.authority_level:
                raise ValueError("authority_level must match the controlling source's authority")
        # No controllable evidence -> this can only be a provisional finding for a human.
        if not controllable and not self.requires_human_review:
            raise ValueError(
                "a finding with no final-authority evidence must set requires_human_review=true"
            )
        return self
