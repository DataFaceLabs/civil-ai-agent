"""Ingestion interfaces for the knowledge layer -- contracts only, no implementations.

This defines the *shape* of an ingestion pipeline (load -> chunk -> index) as typed
Protocols plus the small value objects that flow between the stages, and a planning
helper that turns a registry into per-index ingestion jobs. It intentionally ships **no**
concrete loader, chunker, embedder, or crawler: the heavy ingestion work (fetching
documents, embedding, populating a vector store) is out of scope for this foundation and,
when built, belongs in the data/platform layer behind these interfaces -- the agent repo
owns the contract, not the pipeline.

Depending on abstractions here (Dependency Inversion) means the agent's retrieval code can
be written and tested against fakes today, and a real vector backend can be dropped in
later without touching the agent.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from civilai_agent.knowledge.source_models import (
    AuthorityLevel,
    Domain,
    KnowledgeSource,
    RetrievalIndex,
)


class RawDocument(BaseModel):
    """A fetched document (or a page/part of one) tied back to its registered source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    content: str
    locator: str | None = None
    """Where this came from within the source (page, section, exhibit)."""
    checksum: str | None = None


class DocumentChunk(BaseModel):
    """A retrieval-sized chunk carrying the metadata needed to keep authority attached.

    Authority and index travel *with the chunk* so that a retrieved snippet can never be
    laundered free of its source's authority level -- the retrieval policy and the finding
    contract both key off it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    index: RetrievalIndex
    authority_level: AuthorityLevel
    domains: tuple[Domain, ...] = ()
    locator: str | None = None


class RetrievedChunk(BaseModel):
    """A chunk returned from a similarity query, with its relevance score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk: DocumentChunk
    score: float


@runtime_checkable
class DocumentLoader(Protocol):
    """Fetches raw documents for a registered source (from URL, local path, upload...)."""

    def load(self, source: KnowledgeSource) -> Iterable[RawDocument]: ...


@runtime_checkable
class Chunker(Protocol):
    """Splits a raw document into retrieval-sized chunks, preserving source metadata."""

    def chunk(self, source: KnowledgeSource, document: RawDocument) -> Iterable[DocumentChunk]: ...


@runtime_checkable
class ChunkIndex(Protocol):
    """A retrieval namespace/vector store partition. One logical index per namespace.

    ``query`` may filter by domain so a caller can ask an index only for chunks relevant
    to, say, ``utilities`` -- but it never crosses index boundaries: mixing an ordinance
    and a blog into one undifferentiated store is exactly what the index split prevents.
    """

    def upsert(self, index: RetrievalIndex, chunks: Sequence[DocumentChunk]) -> int: ...

    def query(
        self,
        index: RetrievalIndex,
        text: str,
        *,
        k: int = 8,
        domain: Domain | None = None,
    ) -> Sequence[RetrievedChunk]: ...


class IngestionJob(BaseModel):
    """A planned unit of ingestion: one source into one of its retrieval indexes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    index: RetrievalIndex


def plan_ingestion(sources: Iterable[KnowledgeSource]) -> tuple[IngestionJob, ...]:
    """Expand sources into (source, index) jobs -- one per index a source belongs to.

    Pure and deterministic: no I/O. This is the seam a future scheduler/pipeline drives,
    letting us reason about *what* would be ingested where without building the crawler.
    """
    jobs: list[IngestionJob] = []
    for source in sources:
        for index in source.retrieval_indexes:
            jobs.append(IngestionJob(source_id=source.source_id, index=index))
    return tuple(jobs)
