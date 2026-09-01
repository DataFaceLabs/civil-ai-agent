"""Topic Hydrate brief models (mirror civil-ai-platform topic_brief contract)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

TopicBriefStatus = Literal[
    "complete",
    "partial",
    "summary_only",
    "skipped",
    "disabled",
    "unavailable",
    "no_sections",
]


class TopicCitation(BaseModel):
    """Ordinance citation attached to a topic brief."""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    citation: str = ""
    quote: str = ""


class TopicFieldExtract(BaseModel):
    """Citation-gated field extract from a topic brief."""

    model_config = ConfigDict(extra="forbid")

    fe_code: str
    value: str | float | None = None
    section_id: str | None = None
    quote: str | None = None


class TopicBrief(BaseModel):
    """Closed-world topic hydrate summary for agent narration."""

    model_config = ConfigDict(extra="forbid")

    topic_id: str
    label: str = ""
    status: TopicBriefStatus
    summary: str = ""
    fields: tuple[TopicFieldExtract, ...] = ()
    citations: tuple[TopicCitation, ...] = ()
    guardrails_version: str = ""
    message: str | None = None
