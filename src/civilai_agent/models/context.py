"""Workbench context and agent response contracts (framework-agnostic)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentWorkflow(StrEnum):
    """Named workflows the workbench can request from the agent."""

    MINIMAL_QA = "minimal_qa"
    SECTION_DRAFT = "section_draft"
    GAP_ANALYSIS = "gap_analysis"
    QA_REVIEW = "qa_review"


class WorkbenchContext(BaseModel):
    """Context envelope sent from the workbench / platform."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    entity_id: str | None = None
    snapshot_date: str | None = None
    active_section_id: str | None = None
    selected_artifact_ids: tuple[str, ...] = ()
    selected_source_ids: tuple[str, ...] = ()
    selected_map_layers: tuple[str, ...] = ()
    proposed_use: str | None = None
    user_role: str = "analyst"
    request: str = Field(min_length=1)
    workflow: AgentWorkflow | None = None
    field_context: dict[str, str] = Field(default_factory=dict)
    tenant_id: str | None = None
    user_id: str | None = None


ArtifactType = Literal[
    "finding",
    "risk",
    "draft_section",
    "data_gap",
    "permit_checklist",
    "source_bundle",
    "qa_result",
    "recommended_action",
]


class Claim(BaseModel):
    """A single assertion in an artifact, optionally tied to source refs."""

    model_config = ConfigDict(extra="forbid")

    text: str
    source_refs: tuple[str, ...] = ()


class RecommendedAction(BaseModel):
    """A follow-up the agent suggests; approval-gated by default."""

    model_config = ConfigDict(extra="forbid")

    label: str
    approval_required: bool = True


class AgentArtifact(BaseModel):
    """A typed output unit (draft, finding, gap...) surfaced to the workbench."""

    model_config = ConfigDict(extra="forbid")

    type: ArtifactType
    title: str
    status: str = "partial"
    section_id: str | None = None
    claims: tuple[Claim, ...] = ()
    data_gaps: tuple[str, ...] = ()
    recommended_actions: tuple[RecommendedAction, ...] = ()
    body: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceSummary(BaseModel):
    """Run telemetry: tools used, model, latency, and token counts."""

    model_config = ConfigDict(extra="forbid")

    tools_used: tuple[str, ...] = ()
    sources_used: tuple[str, ...] = ()
    model_id: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    web_search_queries: int = 0
    dedupe_hits: int = 0


class AgentResponse(BaseModel):
    """Framework-agnostic agent response for platform / FE."""

    model_config = ConfigDict(extra="forbid")

    message: str
    artifacts: tuple[AgentArtifact, ...] = ()
    trace_summary: TraceSummary = Field(default_factory=TraceSummary)
    structured_draft: dict[str, Any] | None = None
    guardrail_warnings: tuple[str, ...] = ()
    raw_trace: tuple[dict[str, Any], ...] = ()
