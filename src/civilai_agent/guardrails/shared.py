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

# The required-disclaimer check below used to require an EXACT substring match against
# the canned sentence. Verified against every utilities draft on disk (22/22, 100%): the
# agent always correctly conveys the coverage != capacity caveat in its own words --
# e.g. "coverage does not guarantee capacity or a will-serve commitment", "service-
# territory coverage is not equivalent to confirmed capacity or will-serve" -- but never
# the literal sentence, so the exact-match check was a 100% false positive and had never
# once caught (or could ever catch) a real omission. Check for the CONCEPT instead: one
# sentence pairing a coverage/service-boundary term with a capacity/will-serve term under
# a negation. Falls back to the exact-match behavior for any disclaimer that isn't
# itself phrased around those two concepts (so a differently-worded future disclaimer
# degrades safely rather than silently no-op'ing).
_DISCLAIMER_COVERAGE_TERMS = re.compile(
    r"\b(coverage|service.territory|service.boundar\w*|ccn)\b", re.IGNORECASE
)
_DISCLAIMER_CAPACITY_TERMS = re.compile(r"\b(capacity|will-serve)\b", re.IGNORECASE)
_DISCLAIMER_NEGATION = re.compile(r"\b(not|never|without)\b", re.IGNORECASE)


def _disclaimer_conveyed(disclaimer: str, text: str) -> bool:
    lowered = text.lower()
    if disclaimer.lower() in lowered:
        return True
    disclaimer_lower = disclaimer.lower()
    if not (
        _DISCLAIMER_COVERAGE_TERMS.search(disclaimer_lower)
        and _DISCLAIMER_CAPACITY_TERMS.search(disclaimer_lower)
    ):
        return False
    for sentence in _SENTENCE_SPLIT.split(text):
        s_lower = sentence.lower()
        if (
            _DISCLAIMER_COVERAGE_TERMS.search(s_lower)
            and _DISCLAIMER_CAPACITY_TERMS.search(s_lower)
            and _DISCLAIMER_NEGATION.search(s_lower)
        ):
            return True
    return False


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
    for phrase in guardrails.forbidden_phrases:
        if phrase.strip() and _phrase_flagged(phrase, text):
            warnings.append(f"Output contains forbidden phrase: {phrase!r}")
    if _disclaimer_applies(guardrails, section_id):
        for disclaimer in guardrails.required_disclaimers:
            if disclaimer.strip() and not _disclaimer_conveyed(disclaimer, text):
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
            if disclaimer.strip() and not _disclaimer_conveyed(disclaimer, disclaimer_blob):
                warnings.append(f"Output missing required disclaimer: {disclaimer!r}")
    return tuple(warnings)
