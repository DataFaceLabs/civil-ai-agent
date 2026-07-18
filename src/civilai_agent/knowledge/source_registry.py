"""The knowledge source registry: load, validate, and index :class:`KnowledgeSource`s.

Loads source definitions from a YAML seed file (or an in-memory list, for tests), fails
loudly on duplicate ids or dangling ``supersedes`` references, and offers cheap lookups
by category, retrieval index, domain, and jurisdiction plus staleness detection. It holds
no retrieval *policy* -- ranking and final-finding gating live in ``retrieval_policy``.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path

import yaml

from civilai_agent.knowledge.source_models import (
    Domain,
    KnowledgeSource,
    RetrievalIndex,
    SourceCategory,
)

_SEED_PATH = Path(__file__).parent / "data" / "knowledge_sources.yaml"


class SourceRegistry:
    """An indexed, validated collection of knowledge sources."""

    def __init__(self, sources: Iterable[KnowledgeSource]) -> None:
        by_id: dict[str, KnowledgeSource] = {}
        for source in sources:
            if source.source_id in by_id:
                raise ValueError(f"duplicate source_id: {source.source_id!r}")
            by_id[source.source_id] = source
        # supersedes must reference a source we actually know about (or nothing).
        for source in by_id.values():
            ref = source.supersedes_source_id
            if ref is not None and ref not in by_id:
                raise ValueError(f"source {source.source_id!r} supersedes unknown source {ref!r}")
        self._by_id = by_id

    # -- construction ---------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: Path | str) -> SourceRegistry:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        entries = raw.get("sources", raw if isinstance(raw, list) else [])
        return cls(KnowledgeSource.model_validate(entry) for entry in entries)

    @classmethod
    def from_seed(cls) -> SourceRegistry:
        """Load the packaged seed registry (``data/knowledge_sources.yaml``)."""
        return cls.from_yaml(_SEED_PATH)

    # -- lookups --------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, source_id: str) -> KnowledgeSource | None:
        return self._by_id.get(source_id)

    def all(self) -> tuple[KnowledgeSource, ...]:
        return tuple(self._by_id.values())

    def by_category(self, category: SourceCategory) -> tuple[KnowledgeSource, ...]:
        return tuple(s for s in self._by_id.values() if s.source_category == category)

    def by_index(self, index: RetrievalIndex) -> tuple[KnowledgeSource, ...]:
        return tuple(s for s in self._by_id.values() if index in s.retrieval_indexes)

    def by_domain(self, domain: Domain) -> tuple[KnowledgeSource, ...]:
        return tuple(s for s in self._by_id.values() if s.applies_to_domain(domain))

    def for_jurisdiction(
        self, *, county: str | None = None, city: str | None = None
    ) -> tuple[KnowledgeSource, ...]:
        return tuple(
            s for s in self._by_id.values() if s.applies_to_jurisdiction(county=county, city=city)
        )

    # -- freshness ------------------------------------------------------------------

    def stale_sources(self, as_of: date) -> tuple[KnowledgeSource, ...]:
        """Scheduled sources past their refresh window (never/upload sources excluded)."""
        return tuple(s for s in self._by_id.values() if s.is_stale(as_of))

    def superseded_ids(self) -> frozenset[str]:
        """Ids that some other source declares it supersedes (candidates to retire)."""
        return frozenset(
            s.supersedes_source_id
            for s in self._by_id.values()
            if s.supersedes_source_id is not None
        )
