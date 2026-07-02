"""Guardrail evaluation helpers."""

from __future__ import annotations

from civilai_agent.guardrails.structured import SectionDraftOutput


class GuardrailConfig:
    def __init__(
        self,
        *,
        forbidden_phrases: tuple[str, ...] = (),
        required_disclaimers: tuple[str, ...] = (),
        enforce: bool = False,
    ) -> None:
        self.forbidden_phrases = forbidden_phrases
        self.required_disclaimers = required_disclaimers
        self.enforce = enforce


DEFAULT_GUARDRAILS = GuardrailConfig(
    forbidden_phrases=(
        "will-serve",
        "guaranteed capacity",
        "confirmed service commitment",
    ),
    required_disclaimers=(
        "Utility service boundaries indicate coverage only; capacity and will-serve are not confirmed.",
    ),
    enforce=False,
)


def evaluate_guardrails(text: str, guardrails: GuardrailConfig) -> tuple[str, ...]:
    warnings: list[str] = []
    lowered = text.lower()
    for phrase in guardrails.forbidden_phrases:
        if phrase.strip() and phrase.lower() in lowered:
            warnings.append(f"Output contains forbidden phrase: {phrase!r}")
    for disclaimer in guardrails.required_disclaimers:
        if disclaimer.strip() and disclaimer.lower() not in lowered:
            warnings.append(f"Output missing required disclaimer: {disclaimer!r}")
    return tuple(warnings)


def evaluate_structured_guardrails(
    output: SectionDraftOutput,
    guardrails: GuardrailConfig,
) -> tuple[str, ...]:
    warnings: list[str] = []
    prose = output.suggested_language.lower()
    disclaimer_blob = "\n".join(
        part for part in [output.suggested_language, *output.caveats] if part.strip()
    ).lower()
    for phrase in guardrails.forbidden_phrases:
        if phrase.strip() and phrase.lower() in prose:
            warnings.append(f"Output contains forbidden phrase: {phrase!r}")
    for disclaimer in guardrails.required_disclaimers:
        if disclaimer.strip() and disclaimer.lower() not in disclaimer_blob:
            warnings.append(f"Output missing required disclaimer: {disclaimer!r}")
    return tuple(warnings)
