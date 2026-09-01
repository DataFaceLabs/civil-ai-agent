"""Format Topic Hydrate briefs for section-draft prompts (closed-world)."""

from __future__ import annotations

import json
from collections.abc import Sequence

from civilai_agent.models.topic_brief import TopicBrief

TOPIC_BRIEF_RENDER_RULES = (
    "Topic briefs below are authoritative closed-world reg-text hydrate output. "
    "Paraphrase summaries in suggested_language; do not re-search ordinances or invent "
    "numeric standards absent from brief fields. Treat summary_only, partial, disabled, "
    "and unavailable statuses as verification gaps, not confirmed facts."
)


def format_topic_briefs_block(briefs: Sequence[TopicBrief]) -> str:
    """Serialize topic briefs for pipeline and legacy section-draft prompts."""
    if not briefs:
        return ""
    payload = [
        {
            "topic_id": brief.topic_id,
            "label": brief.label,
            "status": brief.status,
            "summary": brief.summary,
            "fields": [field.model_dump() for field in brief.fields],
            "citations": [cite.model_dump() for cite in brief.citations],
            "message": brief.message,
        }
        for brief in briefs
    ]
    return "\n".join(
        [
            "Topic briefs (authoritative; do not re-search):",
            _compact(payload),
            TOPIC_BRIEF_RENDER_RULES,
        ]
    )


def _compact(obj: object) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)
