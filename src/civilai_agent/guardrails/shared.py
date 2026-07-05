"""Guardrail evaluation helpers."""

from __future__ import annotations

import re

from civilai_agent.guardrails.structured import SectionDraftOutput

# "will-serve" alone is too blunt a match: real drafts consistently and correctly use it
# in safe, recommending/cautionary language ("obtain a will-serve letter", "will-serve
# status is not confirmed"). Only flag a sentence containing "will-serve" when none of
# these markers are also present in that sentence.
_SAFE_WILL_SERVE_MARKERS = (
    "not confirmed",
    "not guaranteed",
    "obtain a will-serve",
    "will-serve letter",
    "will-serve status",
    "will-serve commitment",
    "do not confirm",
    "does not confirm",
    "do not establish",
    "does not establish",
    "pending",
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class GuardrailConfig:
    """Forbidden phrases + required disclaimers evaluated on agent output."""

    def __init__(
        self,
        *,
        forbidden_phrases: tuple[str, ...] = (),
        required_disclaimers: tuple[str, ...] = (),
        disclaimer_sections: frozenset[str] | None = None,
        enforce: bool = False,
    ) -> None:
        self.forbidden_phrases = forbidden_phrases
        self.required_disclaimers = required_disclaimers
        # None means "check on every section" (back-compat default). A set restricts the
        # required-disclaimer check to sections where it's actually relevant -- a soils or
        # jurisdiction draft has no reason to contain a utility-coverage disclaimer, and
        # blanket-checking it made the required-disclaimer warning fire on every single
        # section regardless of content, which made `enforce=True` unusable (F3).
        self.disclaimer_sections = disclaimer_sections
        self.enforce = enforce


DEFAULT_GUARDRAILS = GuardrailConfig(
    forbidden_phrases=(
        "will-serve",
        "guaranteed capacity",
        "confirmed service commitment",
    ),
    required_disclaimers=(
        "Utility service boundaries indicate coverage only; capacity and will-serve are "
        "not confirmed.",
    ),
    disclaimer_sections=frozenset({"utilities"}),
    enforce=False,
)


def _will_serve_flagged(text: str) -> bool:
    for sentence in _SENTENCE_SPLIT.split(text):
        lowered = sentence.lower()
        if "will-serve" in lowered and not any(
            marker in lowered for marker in _SAFE_WILL_SERVE_MARKERS
        ):
            return True
    return False


def _phrase_flagged(phrase: str, text: str) -> bool:
    if phrase.lower() == "will-serve":
        return _will_serve_flagged(text)
    return phrase.lower() in text.lower()


def _disclaimer_applies(guardrails: GuardrailConfig, section_id: str | None) -> bool:
    if guardrails.disclaimer_sections is None:
        return True
    if section_id is None:
        return True
    return section_id in guardrails.disclaimer_sections


def evaluate_guardrails(
    text: str,
    guardrails: GuardrailConfig,
    *,
    section_id: str | None = None,
) -> tuple[str, ...]:
    warnings: list[str] = []
    lowered = text.lower()
    for phrase in guardrails.forbidden_phrases:
        if phrase.strip() and _phrase_flagged(phrase, text):
            warnings.append(f"Output contains forbidden phrase: {phrase!r}")
    if _disclaimer_applies(guardrails, section_id):
        for disclaimer in guardrails.required_disclaimers:
            if disclaimer.strip() and disclaimer.lower() not in lowered:
                warnings.append(f"Output missing required disclaimer: {disclaimer!r}")
    return tuple(warnings)


def evaluate_structured_guardrails(
    output: SectionDraftOutput,
    guardrails: GuardrailConfig,
    *,
    section_id: str | None = None,
) -> tuple[str, ...]:
    warnings: list[str] = []
    prose = output.suggested_language
    disclaimer_blob = "\n".join(
        part for part in [output.suggested_language, *output.caveats] if part.strip()
    )
    for phrase in guardrails.forbidden_phrases:
        if phrase.strip() and _phrase_flagged(phrase, prose):
            warnings.append(f"Output contains forbidden phrase: {phrase!r}")
    if _disclaimer_applies(guardrails, section_id):
        for disclaimer in guardrails.required_disclaimers:
            if disclaimer.strip() and disclaimer.lower() not in disclaimer_blob.lower():
                warnings.append(f"Output missing required disclaimer: {disclaimer!r}")
    return tuple(warnings)
