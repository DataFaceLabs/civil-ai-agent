"""Rewrite leaked unknown-fact phrasing in drafted study prose."""

from __future__ import annotations

import re

from civilai_agent.guardrails.structured import SectionDraftOutput

_UNKNOWN_FACT_REPLACEMENT = "not currently known"

_UNKNOWN_FACT_PATTERNS = (
    re.compile(
        r"\b(?:are|is|were|was)\s+not\s+provided\s+in\s+the\s+available\s+field\s+data\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnot\s+provided\s+in\s+the\s+available\s+field\s+data\b", re.IGNORECASE),
    re.compile(
        r"\b(?:are|is|were|was)\s+not\s+(?:present\s+)?in\s+the\s+available\s+field\s+data\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bnot\s+(?:present\s+)?in\s+the\s+available\s+field\s+data\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:are|is|were|was)\s+not\s+present\s+in\s+(?:the\s+)?field\s+data\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnot\s+present\s+in\s+(?:the\s+)?field\s+data\b", re.IGNORECASE),
    re.compile(r"\bnot\s+available\s+from\s+current\s+project\s+data\b", re.IGNORECASE),
)


def rewrite_unknown_fact_prose(text: str) -> str:
    """Rewrite leaked 'available field data' phrasing; keep the surrounding sentence."""
    cleaned = text or ""
    for pattern in _UNKNOWN_FACT_PATTERNS:
        cleaned = pattern.sub(_UNKNOWN_FACT_REPLACEMENT, cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned)


def rewrite_structured_draft(structured: SectionDraftOutput) -> SectionDraftOutput:
    """Apply unknown-fact rewrites to suggested_language."""
    rewritten = rewrite_unknown_fact_prose(structured.suggested_language)
    if rewritten == structured.suggested_language:
        return structured
    return structured.model_copy(update={"suggested_language": rewritten})
