"""Agent knowledge layer for unstructured/semi-structured sources.

Registry, models, retrieval policy, and ingestion contracts for the sources the
Civil Analyst agent may cite. See ``docs/agent-knowledge-sources.md`` for the
design and rules of use.
"""

from __future__ import annotations

from civilai_agent.knowledge.retrieval_policy import (
    RETRIEVAL_PRIORITY,
    RankedSource,
    RetrievalQuery,
    can_support_final_finding,
    final_finding_candidates,
    rank_sources,
)
from civilai_agent.knowledge.source_models import (
    AUTHORITY_RANK,
    NON_FINAL_AUTHORITY,
    AgentFinding,
    AuthorityLevel,
    Domain,
    EvidenceItem,
    KnowledgeSource,
    RefreshCadence,
    RetrievalIndex,
    SourceCategory,
)
from civilai_agent.knowledge.source_registry import SourceRegistry

__all__ = [
    "AUTHORITY_RANK",
    "NON_FINAL_AUTHORITY",
    "RETRIEVAL_PRIORITY",
    "AgentFinding",
    "AuthorityLevel",
    "Domain",
    "EvidenceItem",
    "KnowledgeSource",
    "RankedSource",
    "RefreshCadence",
    "RetrievalIndex",
    "RetrievalQuery",
    "SourceCategory",
    "SourceRegistry",
    "can_support_final_finding",
    "final_finding_candidates",
    "rank_sources",
]
